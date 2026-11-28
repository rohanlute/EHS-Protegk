
import logging

from openai import OpenAI, APIError, APITimeoutError

from .ai_config import validate_ai_config
from .ai_prompts import (
    HAZOP_SYSTEM_INSTRUCTIONS,
    HAZOP_ANALYSIS_PROMPT,
    HAZOP_REPORT_PROMPT,
)


logger = logging.getLogger(__name__)


class HAZOPAIError(Exception):
    """Base exception for HAZOP AI services."""


class HAZOPAIConfigurationError(HAZOPAIError):
    """Raised when AI configuration is invalid."""


class HAZOPAIServiceError(HAZOPAIError):
    """Raised when the AI provider request fails."""


def get_openai_client():
    """
    Create an OpenAI client using the configured API key.
    """

    try:
        config = validate_ai_config()

    except RuntimeError as exc:
        raise HAZOPAIConfigurationError(str(exc)) from exc

    return OpenAI(
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=2,
    )


def generate_ai_response(
    prompt: str,
    system_instructions: str = HAZOP_SYSTEM_INSTRUCTIONS,
) -> str:
    """
    Generate a text response from the configured AI provider.
    """

    if not prompt or not prompt.strip():
        raise ValueError("AI prompt cannot be empty.")

    try:
        config = validate_ai_config()
        client = get_openai_client()

        response = client.responses.create(
            model=config.model,
            instructions=system_instructions,
            input=prompt,
            max_output_tokens=config.max_output_tokens,
        )

        result = response.output_text

        if not result:
            raise HAZOPAIServiceError(
                "AI provider returned an empty response."
            )

        return result.strip()

    except HAZOPAIConfigurationError:
        raise

    except APITimeoutError as exc:
        logger.exception("HAZOP AI request timed out.")

        raise HAZOPAIServiceError(
            "The AI request timed out. Please try again."
        ) from exc

    except APIError as exc:
        logger.exception("HAZOP AI API error.")

        raise HAZOPAIServiceError(
            "Unable to generate AI response. "
            "Please check the AI service configuration."
        ) from exc

    except HAZOPAIServiceError:
        raise

    except Exception as exc:
        logger.exception("Unexpected HAZOP AI error.")

        raise HAZOPAIServiceError(
            "An unexpected error occurred during AI processing."
        ) from exc


def analyze_hazop_data(hazop_data: dict) -> str:
    """
    Analyze supplied HAZOP data.
    """

    prompt = HAZOP_ANALYSIS_PROMPT.format(
        hazop_data=hazop_data
    )

    return generate_ai_response(prompt)


def generate_hazop_report(study_data: dict) -> str:
    """
    Generate a report draft from supplied HAZOP study data.
    """

    prompt = HAZOP_REPORT_PROMPT.format(
        study_data=study_data
    )

    return generate_ai_response(prompt)
