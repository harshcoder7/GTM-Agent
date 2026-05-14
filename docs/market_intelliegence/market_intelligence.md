we are using signals as search type we can use our deep resaerch agent folder for this

see me_1.webp


from typing import Dict, Optional, Any, List
import requests
import json
from langflow.base.models.model import LCModelComponent
from langflow.field_typing import LanguageModel
from langflow.inputs import MessageTextInput
from langflow.field_typing.range_spec import RangeSpec
from langflow.inputs import IntInput, StrInput, DropdownInput
from langflow.io import Output
from langflow.schema.message import Message

# Define available models and their metadata
MODELS_METADATA = [
    # OpenAI Models
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-4.1-2025-04-14",
    "gpt-4.1-nano-2025-04-14",

    # Gemini Models
    "gemini/gemini-2.5-flash",
    "gemini/gemini-2.0-flash",
    "gemini/gemini-1.5-pro",

    # Anthropic Models
    "anthropic/claude-3.5-sonnet",
]


class DeepQComponent(LCModelComponent):
    display_name = "Research Agent"
    description = "Research agent that performs comprehensive deep research or signals intelligence on topics using Tavily search and LLM."
    icon = "🔎"
    name = "Research Agent"

    inputs = [
        MessageTextInput(
            name="topic",
            display_name="Topic/Lead Data",
            info="Give the topic or URL of your lead domain to research",
            required=True,
        ),
        DropdownInput(
            name="endpoint",
            display_name="Research Type",
            info="Select the type of research to perform",
            options=["research", "signals"],
            value="research",
        ),
        IntInput(
            name="cycles",
            display_name="Research Cycles",
            info="Number of research cycles (1-5)",
            value=2,
            range_spec=RangeSpec(min=1, max=5),
        ),
        MessageTextInput(
            name="api_urls",
            display_name="API URLs",
            info="List of API URLs to try in order. Default URLs will be used if left empty.",
            is_list=True,
            value=["http://localhost:8771", "http://host.docker.internal:8771"],
        ),
        StrInput(
            name="tavily_api_key",
            display_name="Tavily API Key",
            info="Your Tavily API key for search functionality",
            required=True,
        ),
        StrInput(
            name="llm_api_key",
            display_name="API Key",
            info="Your LLM API key",
            required=True,
        ),
        DropdownInput(
            name="model_name",
            display_name="Model Name",
            info="Select the LLM to use for research",
            options=MODELS_METADATA,  # Only show model names
            value="gpt-4o-mini",
        )

    ]

    # Define outputs so other components can connect
    outputs = [
        Output(
            display_name="Research Results",
            name="research_results",
            method="get_research_message",
        ),
        Output(
            display_name="JSON Data",
            name="json_data",
            method="get_json_data",
        ),
        Output(
            display_name="Text Output",
            name="text_output",
            method="get_text_output",
        ),
    ]

    def build_model(self) -> LanguageModel:
        return self

    def _get_api_urls(self) -> List[str]:
        """Get the API URLs list from input"""
        try:
            # If api_urls is provided and not empty, use it
            if self.api_urls and len(self.api_urls) > 0:
                # Filter out empty strings
                urls = [url.strip() for url in self.api_urls if url and url.strip()]
                if urls:
                    return urls

            # Fallback to default URLs if none provided or all empty
            return ["http://localhost:8771", "http://host.docker.internal:8771"]
        except Exception:
            # Fallback to default URLs if any error occurs
            return ["http://localhost:8771", "http://host.docker.internal:8771"]

    def _make_api_request(self) -> Dict[str, Any]:
        """Make the API request and return JSON response"""
        # Get API URLs from input
        api_urls = self._get_api_urls()

        payload = {
            "topic": self.topic,
            "cycles": self.cycles,
            "tavily_api_key": self.tavily_api_key,
            "openai_api_key": self.llm_api_key,
            "openai_model": self.model_name,
            "output_file": "report.md"
        }

        last_error = None

        for base_url in api_urls:
            try:
                # Construct the full API URL with the selected endpoint
                api_url = f"{base_url.rstrip('/')}/{self.endpoint}"

                response = requests.post(
                    api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=300
                )
                
                # Raise an exception for non-200 status codes
                if response.status_code != 200:
                    error_detail = "Unknown error"
                    try:
                        error_response = response.json()
                        error_detail = error_response.get('detail', str(error_response))
                    except:
                        error_detail = response.text or f"HTTP {response.status_code}"
                    
                    raise requests.exceptions.HTTPError(
                        f"API request failed with status {response.status_code}: {error_detail}"
                    )
                
                return response.json()
                
            except requests.exceptions.ConnectionError as e:
                last_error = f"Connection error for {api_url}: {str(e)}"
                continue
            except requests.exceptions.Timeout as e:
                last_error = f"Timeout error for {api_url}: {str(e)}"
                continue
            except requests.exceptions.HTTPError as e:
                last_error = f"HTTP error for {api_url}: {str(e)}"
                continue
            except requests.exceptions.RequestException as e:
                last_error = f"Request error for {api_url}: {str(e)}"
                continue

        # If we get here, all URLs failed - raise the exception instead of returning error dict
        raise Exception(f"Could not connect to research API on any of the provided URLs: {', '.join(api_urls)}. Last error: {last_error}")

    def get_research_message(self) -> Message:
        """Return only the final report as Message object, without repeating the question/topic."""
        json_response = self._make_api_request()
        # Only show the final_report, no topic/question heading
        text = json_response.get('final_report', 'No final report available.')
        self.log(json_response.get('usage_summary', 'No usage summary provided'))
        return Message(
            text=text,
            sender="DeepQ",
            sender_name="Research Assistant"
        )

    def get_json_data(self) -> Message:
        """Return raw JSON data as Message object"""
        json_response = self._make_api_request()
        json_text = json.dumps(json_response, indent=2, ensure_ascii=False)

        return Message(
            text=json_text,
            sender="DeepQ",
            sender_name="JSON Data"
        )

    def get_text_output(self) -> str:
        """Return JSON as string for Text Output"""
        json_response = self._make_api_request()
        return json.dumps(json_response, indent=2, ensure_ascii=False)
