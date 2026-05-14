
this is the code the for for the lead enrichment flow in langflow le_1.webp 
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


and after this you already have the code in deep-resaerch-agent-sdr where everythinf is written and how will be expose the port and everything


we have structured output component refer le_2.webp

in structured output we are collected this coloumns thats why we have defined the schema 


from pydantic import BaseModel, Field, create_model
from trustcall import create_extractor

from langflow.base.models.chat_result import get_chat_result
from langflow.custom.custom_component.component import Component
from langflow.helpers.base_model import build_model_from_schema
from langflow.io import (
    HandleInput,
    MessageTextInput,
    MultilineInput,
    Output,
    TableInput,
)
from langflow.schema.data import Data
from langflow.schema.table import EditMode


class StructuredOutputComponent(Component):
    display_name = "Structured Output"
    description = "Uses an LLM to generate structured data. Ideal for extraction and consistency."
    name = "StructuredOutput"
    icon = "braces"

    inputs = [
        HandleInput(
            name="llm",
            display_name="Language Model",
            info="The language model to use to generate the structured output.",
            input_types=["LanguageModel"],
            required=True,
        ),
        MessageTextInput(
            name="input_value",
            display_name="Input Message",
            info="The input message to the language model.",
            tool_mode=True,
            required=True,
        ),
        MultilineInput(
            name="system_prompt",
            display_name="Format Instructions",
            info="The instructions to the language model for formatting the output.",
            value=(
                "You are an AI system designed to extract structured information from unstructured text."
                "Given the input_text, return a JSON object with predefined keys based on the expected structure."
                "Extract values accurately and format them according to the specified type "
                "(e.g., string, integer, float, date)."
                "If a value is missing or cannot be determined, return a default "
                "(e.g., null, 0, or 'N/A')."
                "If multiple instances of the expected structure exist within the input_text, "
                "stream each as a separate JSON object."
            ),
            required=True,
            advanced=True,
        ),
        MessageTextInput(
            name="schema_name",
            display_name="Schema Name",
            info="Provide a name for the output data schema.",
            advanced=True,
        ),
        TableInput(
            name="output_schema",
            display_name="Output Schema",
            info="Define the structure and data types for the model's output.",
            required=True,
            # TODO: remove deault value
            table_schema=[
                {
                    "name": "name",
                    "display_name": "Name",
                    "type": "str",
                    "description": "Specify the name of the output field.",
                    "default": "field",
                    "edit_mode": EditMode.INLINE,
                },
                {
                    "name": "description",
                    "display_name": "Description",
                    "type": "str",
                    "description": "Describe the purpose of the output field.",
                    "default": "description of field",
                    "edit_mode": EditMode.POPOVER,
                },
                {
                    "name": "type",
                    "display_name": "Type",
                    "type": "str",
                    "edit_mode": EditMode.INLINE,
                    "description": ("Indicate the data type of the output field (e.g., str, int, float, bool, dict)."),
                    "options": ["str", "int", "float", "bool", "dict"],
                    "default": "str",
                },
                {
                    "name": "multiple",
                    "display_name": "As List",
                    "type": "boolean",
                    "description": "Set to True if this output field should be a list of the specified type.",
                    "default": "False",
                    "edit_mode": EditMode.INLINE,
                },
            ],
            value=[
                {
                    "name": "field",
                    "description": "description of field",
                    "type": "str",
                    "multiple": "False",
                }
            ],
        ),
    ]

    outputs = [
        Output(
            name="structured_output",
            display_name="Structured Output",
            method="build_structured_output",
        ),
    ]

    def build_structured_output_base(self):
        schema_name = self.schema_name or "OutputModel"

        if not hasattr(self.llm, "with_structured_output"):
            msg = "Language model does not support structured output."
            raise TypeError(msg)
        if not self.output_schema:
            msg = "Output schema cannot be empty"
            raise ValueError(msg)

        output_model_ = build_model_from_schema(self.output_schema)

        output_model = create_model(
            schema_name,
            __doc__=f"A list of {schema_name}.",
            objects=(list[output_model_], Field(description=f"A list of {schema_name}.")),  # type: ignore[valid-type]
        )

        try:
            llm_with_structured_output = create_extractor(self.llm, tools=[output_model])
        except NotImplementedError as exc:
            msg = f"{self.llm.__class__.__name__} does not support structured output."
            raise TypeError(msg) from exc

        config_dict = {
            "run_name": self.display_name,
            "project_name": self.get_project_name(),
            "callbacks": self.get_langchain_callbacks(),
        }
        result = get_chat_result(
            runnable=llm_with_structured_output,
            system_message=self.system_prompt,
            input_value=self.input_value,
            config=config_dict,
        )

        # OPTIMIZATION NOTE: Simplified processing based on trustcall response structure
        # Handle non-dict responses (shouldn't happen with trustcall, but defensive)
        if not isinstance(result, dict):
            return result

        # Extract first response and convert BaseModel to dict
        responses = result.get("responses", [])
        if not responses:
            return result

        # Convert BaseModel to dict (creates the "objects" key)
        first_response = responses[0]
        structured_data = first_response.model_dump() if isinstance(first_response, BaseModel) else first_response

        # Extract the objects array (guaranteed to exist due to our Pydantic model structure)
        return structured_data.get("objects", structured_data)

    def build_structured_output(self) -> Data:
        output = self.build_structured_output_base()
        if not isinstance(output, list) or not output:
            # handle empty or unexpected type case
            msg = "No structured output returned"
            raise ValueError(msg)
        if len(output) != 1:
            msg = "Multiple structured outputs returned"
            raise ValueError(msg)
        return Data(data=output[0])


this is the code for structured output component adn i think a llm will be used for usong the structued output 


this is the code for chatoutput

lso read in detailed about resaerch type in the deep resaerch agent sdr folder how its done

now after this we have icp flow and i think we are dtaking data for each of the flow in form of parser we are somehow parsing the vlaues



import json
import string
from typing import Any, cast

from apify_client import ApifyClient
from langchain_community.document_loaders.apify_dataset import ApifyDatasetLoader
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, field_serializer

from langflow.custom.custom_component.component import Component
from langflow.field_typing import Tool
from langflow.inputs.inputs import BoolInput
from langflow.io import MultilineInput, Output, SecretStrInput, StrInput
from langflow.schema.data import Data

MAX_DESCRIPTION_LEN = 250


class ApifyActorsComponent(Component):
    display_name = "Apify Actors"
    description = (
        "Use Apify Actors to extract data from hundreds of places fast. "
        "This component can be used in a flow to retrieve data or as a tool with an agent."
    )
    documentation: str = "http://docs.langflow.org/integrations-apify"
    icon = "Apify"
    name = "ApifyActors"

    inputs = [
        SecretStrInput(
            name="apify_token",
            display_name="Apify Token",
            info="The API token for the Apify account.",
            required=True,
            password=True,
        ),
        StrInput(
            name="actor_id",
            display_name="Actor",
            info=(
                "Actor name from Apify store to run. For example 'apify/website-content-crawler' "
                "to use the Website Content Crawler Actor."
            ),
            value="apify/website-content-crawler",
            required=True,
        ),
        # multiline input is more pleasant to use than the nested dict input
        MultilineInput(
            name="run_input",
            display_name="Run input",
            info=(
                'The JSON input for the Actor run. For example for the "apify/website-content-crawler" Actor: '
                '{"startUrls":[{"url":"https://docs.apify.com/academy/web-scraping-for-beginners"}],"maxCrawlDepth":0}'
            ),
            value='{"startUrls":[{"url":"https://docs.apify.com/academy/web-scraping-for-beginners"}],"maxCrawlDepth":0}',
            required=True,
        ),
        MultilineInput(
            name="dataset_fields",
            display_name="Output fields",
            info=(
                "Fields to extract from the dataset, split by commas. "
                "Other fields will be ignored. Dots in nested structures will be replaced by underscores. "
                "Sample input: 'text, metadata.title'. "
                "Sample output: {'text': 'page content here', 'metadata_title': 'page title here'}. "
                "For example, for the 'apify/website-content-crawler' Actor, you can extract the 'markdown' field, "
                "which is the content of the website in markdown format."
            ),
        ),
        BoolInput(
            name="flatten_dataset",
            display_name="Flatten output",
            info=(
                "The output dataset will be converted from a nested format to a flat structure. "
                "Dots in nested structure will be replaced by underscores. "
                "This is useful for further processing of the Data object. "
                "For example, {'a': {'b': 1}} will be flattened to {'a_b': 1}."
            ),
        ),
    ]

    outputs = [
        Output(display_name="Output", name="output", type_=list[Data], method="run_model"),
        Output(display_name="Tool", name="tool", type_=Tool, method="build_tool"),
    ]

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._apify_client: ApifyClient | None = None

    def run_model(self) -> list[Data]:
        """Run the Actor and return node output."""
        input_ = json.loads(self.run_input)
        fields = ApifyActorsComponent.parse_dataset_fields(self.dataset_fields) if self.dataset_fields else None
        res = self._run_actor(self.actor_id, input_, fields=fields)
        if self.flatten_dataset:
            res = [ApifyActorsComponent.flatten(item) for item in res]
        data = [Data(data=item) for item in res]

        self.status = data
        return data

    def build_tool(self) -> Tool:
        """Build a tool for an agent that runs the Apify Actor."""
        actor_id = self.actor_id

        build = self._get_actor_latest_build(actor_id)
        readme = build.get("readme", "")[:250] + "..."
        if not (input_schema_str := build.get("inputSchema")):
            msg = "Input schema not found"
            raise ValueError(msg)
        input_schema = json.loads(input_schema_str)
        properties, required = ApifyActorsComponent.get_actor_input_schema_from_build(input_schema)
        properties = {"run_input": properties}

        # works from input schema
        info_ = [
            (
                "JSON encoded as a string with input schema (STRICTLY FOLLOW JSON FORMAT AND SCHEMA):\n\n"
                f"{json.dumps(properties, separators=(',', ':'))}"
            )
        ]
        if required:
            info_.append("\n\nRequired fields:\n" + "\n".join(required))

        info = "".join(info_)

        input_model_cls = ApifyActorsComponent.create_input_model_class(info)
        tool_cls = ApifyActorsComponent.create_tool_class(self, readme, input_model_cls, actor_id)

        return cast("Tool", tool_cls())

    @staticmethod
    def create_tool_class(
        parent: "ApifyActorsComponent", readme: str, input_model: type[BaseModel], actor_id: str
    ) -> type[BaseTool]:
        """Create a tool class that runs an Apify Actor."""

        class ApifyActorRun(BaseTool):
            """Tool that runs Apify Actors."""

            name: str = f"apify_actor_{ApifyActorsComponent.actor_id_to_tool_name(actor_id)}"
            description: str = (
                "Run an Apify Actor with the given input. "
                "Here is a part of the currently loaded Actor README:\n\n"
                f"{readme}\n\n"
            )

            args_schema: type[BaseModel] = input_model

            @field_serializer("args_schema")
            def serialize_args_schema(self, args_schema):
                return args_schema.schema()

            def _run(self, run_input: str | dict) -> str:
                """Use the Apify Actor."""
                input_dict = json.loads(run_input) if isinstance(run_input, str) else run_input

                # retrieve if nested, just in case
                input_dict = input_dict.get("run_input", input_dict)

                res = parent._run_actor(actor_id, input_dict)
                return "\n\n".join([ApifyActorsComponent.dict_to_json_str(item) for item in res])

        return ApifyActorRun

    @staticmethod
    def create_input_model_class(description: str) -> type[BaseModel]:
        """Create a Pydantic model class for the Actor input."""

        class ActorInput(BaseModel):
            """Input for the Apify Actor tool."""

            run_input: str = Field(..., description=description)

        return ActorInput

    def _get_apify_client(self) -> ApifyClient:
        """Get the Apify client.

        Is created if not exists or token changes.
        """
        if not self.apify_token:
            msg = "API token is required."
            raise ValueError(msg)
        # when token changes, create a new client
        if self._apify_client is None or self._apify_client.token != self.apify_token:
            self._apify_client = ApifyClient(self.apify_token)
            if httpx_client := self._apify_client.http_client.httpx_client:
                httpx_client.headers["user-agent"] += "; Origin/langflow"
        return self._apify_client

    def _get_actor_latest_build(self, actor_id: str) -> dict:
        """Get the latest build of an Actor from the default build tag."""
        client = self._get_apify_client()
        actor = client.actor(actor_id=actor_id)
        if not (actor_info := actor.get()):
            msg = f"Actor {actor_id} not found."
            raise ValueError(msg)

        default_build_tag = actor_info.get("defaultRunOptions", {}).get("build")
        latest_build_id = actor_info.get("taggedBuilds", {}).get(default_build_tag, {}).get("buildId")

        if (build := client.build(latest_build_id).get()) is None:
            msg = f"Build {latest_build_id} not found."
            raise ValueError(msg)

        return build

    @staticmethod
    def get_actor_input_schema_from_build(input_schema: dict) -> tuple[dict, list[str]]:
        """Get the input schema from the Actor build.

        Trim the description to 250 characters.
        """
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        properties_out: dict = {}
        for item, meta in properties.items():
            properties_out[item] = {}
            if desc := meta.get("description"):
                properties_out[item]["description"] = (
                    desc[:MAX_DESCRIPTION_LEN] + "..." if len(desc) > MAX_DESCRIPTION_LEN else desc
                )
            for key_name in ("type", "default", "prefill", "enum"):
                if value := meta.get(key_name):
                    properties_out[item][key_name] = value

        return properties_out, required

    def _get_run_dataset_id(self, run_id: str) -> str:
        """Get the dataset id from the run id."""
        client = self._get_apify_client()
        run = client.run(run_id=run_id)
        if (dataset := run.dataset().get()) is None:
            msg = "Dataset not found"
            raise ValueError(msg)
        if (did := dataset.get("id")) is None:
            msg = "Dataset id not found"
            raise ValueError(msg)
        return did

    @staticmethod
    def dict_to_json_str(d: dict) -> str:
        """Convert a dictionary to a JSON string."""
        return json.dumps(d, separators=(",", ":"), default=lambda _: "<n/a>")

    @staticmethod
    def actor_id_to_tool_name(actor_id: str) -> str:
        """Turn actor_id into a valid tool name.

        Tool name must only contain letters, numbers, underscores, dashes,
            and cannot contain spaces.
        """
        valid_chars = string.ascii_letters + string.digits + "_-"
        return "".join(char if char in valid_chars else "_" for char in actor_id)

    def _run_actor(self, actor_id: str, run_input: dict, fields: list[str] | None = None) -> list[dict]:
        """Run an Apify Actor and return the output dataset.

        Args:
            actor_id: Actor name from Apify store to run.
            run_input: JSON input for the Actor.
            fields: List of fields to extract from the dataset. Other fields will be ignored.
        """
        client = self._get_apify_client()
        if (details := client.actor(actor_id=actor_id).call(run_input=run_input, wait_secs=1)) is None:
            msg = "Actor run details not found"
            raise ValueError(msg)
        if (run_id := details.get("id")) is None:
            msg = "Run id not found"
            raise ValueError(msg)

        if (run_client := client.run(run_id)) is None:
            msg = "Run client not found"
            raise ValueError(msg)

        # stream logs
        with run_client.log().stream() as response:
            if response:
                for line in response.iter_lines():
                    self.log(line)
        run_client.wait_for_finish()

        dataset_id = self._get_run_dataset_id(run_id)

        loader = ApifyDatasetLoader(
            dataset_id=dataset_id,
            dataset_mapping_function=lambda item: item
            if not fields
            else {k.replace(".", "_"): ApifyActorsComponent.get_nested_value(item, k) for k in fields},
        )
        return loader.load()

    @staticmethod
    def get_nested_value(data: dict[str, Any], key: str) -> Any:
        """Get a nested value from a dictionary."""
        keys = key.split(".")
        value = data
        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return None
            value = value[k]
        return value

    @staticmethod
    def parse_dataset_fields(dataset_fields: str) -> list[str]:
        """Convert a string of comma-separated fields into a list of fields."""
        dataset_fields = dataset_fields.replace("'", "").replace('"', "").replace("`", "")
        return [field.strip() for field in dataset_fields.split(",")]

    @staticmethod
    def flatten(d: dict) -> dict:
        """Flatten a nested dictionary."""

        def items():
            for key, value in d.items():
                if isinstance(value, dict):
                    for subkey, subvalue in ApifyActorsComponent.flatten(value).items():
                        yield key + "_" + subkey, subvalue
                else:
                    yield key, value

        return dict(items())
 