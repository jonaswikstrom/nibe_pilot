import logging
import json
import asyncio
from datetime import datetime
from typing import Any
from anthropic import (
    AsyncAnthropic,
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    APIStatusError,
)

from .const import CLAUDE_MODEL, MAX_HEAT_CURVE_DELTA, MAX_HEAT_OFFSET_DELTA

API_TIMEOUT = 30.0
MAX_RETRIES = 3
RETRY_DELAYS = [1, 2, 4]

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du är en expert på värmepumpsoptimering för Nibe frånluftsvärmepumpar.
Din uppgift är att analysera sensordata och väderprognos för att ge optimala styrningsrekommendationer.

VIKTIGA PRINCIPER:
1. Prioritera komfort - inomhustemperaturen ska vara stabil nära börvärdet
2. Optimera energieffektivitet när det inte påverkar komforten
3. Använd väderprognos för att förutse värmebehov
4. Undvik onödiga ändringar - små avvikelser kräver ingen åtgärd
5. Var konservativ med ändringar - hellre små justeringar ofta än stora sällan

ELPRISOPTIMERING (om prisdata finns):
- BILLIG TIMME (under genomsnitt): Öka värmeoffset (+1 till +3) för att lagra värme i huset
- DYR TIMME (över genomsnitt): Minska värmeoffset (-1 till -3) för att utnyttja lagrad värme
- Anpassa aggressiviteten efter byggnadstyp:
  * Lätt byggnad: max ±1 (värmen försvinner snabbt)
  * Normal byggnad: max ±2
  * Tung byggnad: max ±3 (kan lagra mycket värme)
- Vid mycket dyra priser (>50% över snitt): prioritera kostnadsbesparing mer aggressivt
- Kombinera med väderprognos: förladda värme innan kall period + dyra timmar

BEGRÄNSNINGAR:
- Värmekurva-justering: max ±5 per analys
- Värmeoffset-justering: max ±3 per analys

Svara ENDAST med valid JSON i följande format:
{
  "action": "adjust_heat_curve|adjust_offset|no_change",
  "heat_curve_delta": <-5 till +5, eller 0>,
  "heat_offset_delta": <-3 till +3, eller 0>,
  "reasoning": "<kort förklaring på svenska>",
  "confidence": <0.0 till 1.0>
}"""


def build_user_prompt(data: dict[str, Any]) -> str:
    now = datetime.now()
    prompt_parts = [
        f"TIDPUNKT: {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')})",
        "",
        "NUVARANDE TILLSTÅND:"
    ]

    if data.get("outdoor_temp") is not None:
        prompt_parts.append(f"- Utomhustemperatur: {data['outdoor_temp']}°C")
    if data.get("indoor_temp") is not None:
        prompt_parts.append(f"- Inomhustemperatur: {data['indoor_temp']}°C")
    if data.get("setpoint") is not None:
        prompt_parts.append(f"- Börvärde: {data['setpoint']}°C")
    if data.get("supply_temp") is not None:
        prompt_parts.append(f"- Framledningstemperatur: {data['supply_temp']}°C")
    if data.get("return_temp") is not None:
        prompt_parts.append(f"- Returtemperatur: {data['return_temp']}°C")
    if data.get("heat_curve") is not None:
        prompt_parts.append(f"- Värmekurva: {data['heat_curve']}")
    if data.get("heat_offset") is not None:
        prompt_parts.append(f"- Värmeoffset: {data['heat_offset']}")
    if data.get("compressor_freq") is not None:
        prompt_parts.append(f"- Kompressorfrekvens: {data['compressor_freq']} Hz")
    if data.get("power_consumption") is not None:
        prompt_parts.append(f"- Elförbrukning: {data['power_consumption']} W")
    if data.get("hot_water_temp") is not None:
        prompt_parts.append(f"- Varmvattentemperatur: {data['hot_water_temp']}°C")

    if data.get("weather_forecast"):
        prompt_parts.append("\nVÄDERPROGNOS (kommande 24h):")
        for forecast in data["weather_forecast"][:8]:
            prompt_parts.append(
                f"- {forecast.get('datetime', 'N/A')}: "
                f"{forecast.get('temperature', 'N/A')}°C, "
                f"{forecast.get('condition', 'N/A')}"
            )

    if data.get("electricity_prices"):
        prices = data["electricity_prices"]
        price_values = [p.get("price") for p in prices if p.get("price") is not None]

        if price_values:
            avg_price = sum(price_values) / len(price_values)
            min_price = min(price_values)
            max_price = max(price_values)
            current_price = price_values[0] if price_values else None

            prompt_parts.append("\nELPRIS:")
            prompt_parts.append(f"- Nuvarande pris: {current_price:.1f} öre/kWh")
            prompt_parts.append(f"- Genomsnitt (24h): {avg_price:.1f} öre/kWh")
            prompt_parts.append(f"- Lägsta: {min_price:.1f} öre/kWh")
            prompt_parts.append(f"- Högsta: {max_price:.1f} öre/kWh")

            if current_price:
                price_diff_pct = ((current_price - avg_price) / avg_price) * 100
                if price_diff_pct < -20:
                    prompt_parts.append(f"- Status: BILLIGT ({price_diff_pct:.0f}% under snitt)")
                elif price_diff_pct > 20:
                    prompt_parts.append(f"- Status: DYRT ({price_diff_pct:.0f}% över snitt)")
                else:
                    prompt_parts.append(f"- Status: NORMALT ({price_diff_pct:+.0f}% vs snitt)")

            prompt_parts.append("\nKommande timmar:")
            for price in prices[:6]:
                hour_price = price.get("price")
                if hour_price is not None:
                    indicator = "↓" if hour_price < avg_price * 0.8 else "↑" if hour_price > avg_price * 1.2 else "→"
                    prompt_parts.append(
                        f"  {price.get('hour', 'N/A')}: {hour_price:.1f} öre/kWh {indicator}"
                    )
        else:
            prompt_parts.append("\nELPRIS (kommande timmar):")
            for price in prices[:8]:
                prompt_parts.append(
                    f"- {price.get('hour', 'N/A')}: {price.get('price', 'N/A')} öre/kWh"
                )

    if data.get("last_action"):
        prompt_parts.append("\nSENASTE JUSTERING:")
        last = data["last_action"]
        prompt_parts.append(f"- Åtgärd: {last.get('action', 'okänd')}")
        if last.get("delta"):
            prompt_parts.append(f"- Justering: {last.get('delta')}")
        if last.get("timestamp"):
            prompt_parts.append(f"- Tidpunkt: {last.get('timestamp')}")

    if data.get("building_type"):
        prompt_parts.append(f"\nBYGGNADSTYP: {data['building_type']}")

    prompt_parts.append("\nGe din rekommendation baserat på ovanstående data.")

    return "\n".join(prompt_parts)


class ClaudeService:
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._client: AsyncAnthropic | None = None
        self.api_available = True
        self.last_error: str | None = None
        self.consecutive_failures = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.api_calls_count = 0

    @property
    def client(self) -> AsyncAnthropic:
        if self._client is None:
            self._client = AsyncAnthropic(api_key=self._api_key, timeout=API_TIMEOUT)
        return self._client

    async def get_recommendation(self, data: dict[str, Any]) -> dict[str, Any]:
        user_prompt = build_user_prompt(data)

        _LOGGER.debug("Sending request to Claude API")
        _LOGGER.debug("User prompt: %s", user_prompt)

        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                response = await self.client.messages.create(
                    model=CLAUDE_MODEL,
                    max_tokens=500,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}]
                )

                self.api_available = True
                self.last_error = None
                self.consecutive_failures = 0
                self.api_calls_count += 1

                if hasattr(response, 'usage') and response.usage:
                    self.last_input_tokens = response.usage.input_tokens
                    self.last_output_tokens = response.usage.output_tokens
                    self.total_input_tokens += self.last_input_tokens
                    self.total_output_tokens += self.last_output_tokens
                    _LOGGER.debug(
                        "Token usage - Input: %d, Output: %d, Total: %d/%d",
                        self.last_input_tokens, self.last_output_tokens,
                        self.total_input_tokens, self.total_output_tokens
                    )

                _LOGGER.debug("Claude response received (attempt %d)", attempt + 1)
                _LOGGER.debug("Stop reason: %s", response.stop_reason)

                if not response.content:
                    _LOGGER.error("Claude returned empty content")
                    return self._default_response("Tomt svar från AI")

                response_text = response.content[0].text
                _LOGGER.debug("Claude response text: %s", response_text)

                if not response_text or not response_text.strip():
                    _LOGGER.error("Claude returned empty text")
                    return self._default_response("Tomt textsvar från AI")

                clean_text = response_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                if clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                result = json.loads(clean_text)
                result = self._validate_and_clamp(result)

                return result

            except APITimeoutError as e:
                last_exception = e
                _LOGGER.warning(
                    "Claude API timeout (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, e
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])

            except APIConnectionError as e:
                last_exception = e
                _LOGGER.warning(
                    "Claude API connection error (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, e
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])

            except RateLimitError as e:
                last_exception = e
                _LOGGER.warning(
                    "Claude API rate limit (attempt %d/%d): %s",
                    attempt + 1, MAX_RETRIES, e
                )
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt] * 2)

            except APIStatusError as e:
                _LOGGER.error("Claude API error (status %d): %s", e.status_code, e.message)
                self._record_failure(f"API-fel (HTTP {e.status_code})")
                return self._default_response(f"API-fel: {e.message}")

            except json.JSONDecodeError as e:
                _LOGGER.error("Failed to parse Claude response as JSON: %s", e)
                return self._default_response("Kunde inte tolka AI-svaret")

            except Exception as e:
                _LOGGER.error("Unexpected error calling Claude API: %s", e, exc_info=True)
                self._record_failure(str(e))
                return self._default_response(f"Oväntat fel: {str(e)}")

        self._record_failure(f"Timeout efter {MAX_RETRIES} försök")
        _LOGGER.error(
            "Claude API failed after %d attempts. Last error: %s",
            MAX_RETRIES, last_exception
        )
        return self._default_response(f"API otillgängligt efter {MAX_RETRIES} försök")

    def _record_failure(self, error: str):
        self.consecutive_failures += 1
        self.last_error = error
        if self.consecutive_failures >= 3:
            self.api_available = False
            _LOGGER.error(
                "Claude API marked as unavailable after %d consecutive failures",
                self.consecutive_failures
            )

    def _validate_and_clamp(self, result: dict[str, Any]) -> dict[str, Any]:
        if "action" not in result:
            result["action"] = "no_change"

        heat_curve_delta = result.get("heat_curve_delta", 0)
        result["heat_curve_delta"] = max(
            -MAX_HEAT_CURVE_DELTA,
            min(MAX_HEAT_CURVE_DELTA, heat_curve_delta)
        )

        heat_offset_delta = result.get("heat_offset_delta", 0)
        result["heat_offset_delta"] = max(
            -MAX_HEAT_OFFSET_DELTA,
            min(MAX_HEAT_OFFSET_DELTA, heat_offset_delta)
        )

        confidence = result.get("confidence", 0.5)
        result["confidence"] = max(0.0, min(1.0, confidence))

        if "reasoning" not in result:
            result["reasoning"] = "Ingen förklaring given"

        return result

    def _default_response(self, reason: str) -> dict[str, Any]:
        return {
            "action": "no_change",
            "heat_curve_delta": 0,
            "heat_offset_delta": 0,
            "reasoning": reason,
            "confidence": 0.0
        }

    @property
    def token_stats(self) -> dict[str, Any]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "last_input_tokens": self.last_input_tokens,
            "last_output_tokens": self.last_output_tokens,
            "last_tokens": self.last_input_tokens + self.last_output_tokens,
            "api_calls_count": self.api_calls_count,
        }

    async def validate_api_key(self) -> bool:
        try:
            await self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            _LOGGER.error("API key validation failed: %s", e)
            return False
