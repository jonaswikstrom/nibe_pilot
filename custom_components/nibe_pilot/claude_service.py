import logging
import json
from typing import Any
from anthropic import AsyncAnthropic

from .const import CLAUDE_MODEL, MAX_HEAT_CURVE_DELTA, MAX_HEAT_OFFSET_DELTA

_LOGGER = logging.getLogger(__name__)

SYSTEM_PROMPT = """Du är en expert på värmepumpsoptimering för Nibe frånluftsvärmepumpar.
Din uppgift är att analysera sensordata och väderprognos för att ge optimala styrningsrekommendationer.

VIKTIGA PRINCIPER:
1. Prioritera komfort - inomhustemperaturen ska vara stabil nära börvärdet
2. Optimera energieffektivitet när det inte påverkar komforten
3. Använd väderprognos för att förutse värmebehov
4. Om elpris finns: överväg att förskjuta last till billigare timmar
5. Undvik onödiga ändringar - små avvikelser kräver ingen åtgärd
6. Var konservativ med ändringar - hellre små justeringar ofta än stora sällan

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
    prompt_parts = ["NUVARANDE TILLSTÅND:"]

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
        prompt_parts.append("\nELPRIS (kommande timmar):")
        for price in data["electricity_prices"][:8]:
            prompt_parts.append(
                f"- {price.get('hour', 'N/A')}: {price.get('price', 'N/A')} öre/kWh"
            )

    prompt_parts.append("\nGe din rekommendation baserat på ovanstående data.")

    return "\n".join(prompt_parts)


class ClaudeService:
    def __init__(self, api_key: str):
        self.client = AsyncAnthropic(api_key=api_key)

    async def get_recommendation(self, data: dict[str, Any]) -> dict[str, Any]:
        user_prompt = build_user_prompt(data)

        _LOGGER.debug("Sending request to Claude API")
        _LOGGER.debug("User prompt: %s", user_prompt)

        try:
            response = await self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            _LOGGER.debug("Claude response object: %s", response)
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

        except json.JSONDecodeError as e:
            _LOGGER.error("Failed to parse Claude response as JSON: %s", e)
            _LOGGER.error("Response text was: %s", response_text if 'response_text' in dir() else 'N/A')
            return self._default_response("Kunde inte tolka AI-svaret")
        except Exception as e:
            _LOGGER.error("Error calling Claude API: %s", e, exc_info=True)
            return self._default_response(f"API-fel: {str(e)}")

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
