soo this is the flow i want you to design this very carefully cause we also have gmail option through which we can send emails automatically

see ef_1.webp

the code for load csv with row slicing is 


import csv
import io
from pathlib import Path
from langflow.custom import Component
from langflow.io import FileInput, MessageTextInput, MultilineInput, IntInput, Output
from langflow.schema import Data

class CSVToDataComponent(Component):
    display_name = "Load CSV with Row Slicing"
    description = "Load a CSV file, CSV from a file path, or a valid CSV string and convert it to a list of Data with optional row slicing"
    icon = "file-spreadsheet"
    name = "CSVtoData"
    legacy = True
    
    inputs = [
        FileInput(
            name="csv_file",
            display_name="CSV File",
            file_types=["csv"],
            info="Upload a CSV file to convert to a list of Data objects",
        ),
        MessageTextInput(
            name="csv_path",
            display_name="CSV File Path",
            info="Provide the path to the CSV file as pure text",
        ),
        MultilineInput(
            name="csv_string",
            display_name="CSV String",
            info="Paste a CSV string directly to convert to a list of Data objects",
        ),
        MessageTextInput(
            name="text_key",
            display_name="Text Key",
            info="The key to use for the text column. Defaults to 'text'.",
            value="text",
        ),
        IntInput(
            name="start_index",
            display_name="Start Index",
            info="Starting row index (0-based). Leave empty to start from beginning.",
            value=0,
        ),
        IntInput(
            name="stop_index",
            display_name="Stop Index",
            info="Stopping row index (exclusive). Leave empty to include all rows to the end.",
            value=None,
        ),
    ]
    
    outputs = [
        Output(name="data_list", display_name="Data List", method="load_csv_to_data"),
    ]
    
    def load_csv_to_data(self) -> list[Data]:
        if sum(bool(field) for field in [self.csv_file, self.csv_path, self.csv_string]) != 1:
            msg = "Please provide exactly one of: CSV file, file path, or CSV string."
            raise ValueError(msg)
        
        csv_data = None
        
        try:
            if self.csv_file:
                resolved_path = self.resolve_path(self.csv_file)
                file_path = Path(resolved_path)
                if file_path.suffix.lower() != ".csv":
                    self.status = "The provided file must be a CSV file."
                else:
                    with file_path.open(newline="", encoding="utf-8") as csvfile:
                        csv_data = csvfile.read()
            elif self.csv_path:
                file_path = Path(self.csv_path)
                if file_path.suffix.lower() != ".csv":
                    self.status = "The provided file must be a CSV file."
                else:
                    with file_path.open(newline="", encoding="utf-8") as csvfile:
                        csv_data = csvfile.read()
            else:
                csv_data = self.csv_string
            
            if csv_data:
                csv_reader = csv.DictReader(io.StringIO(csv_data))
                all_rows = [Data(data=row, text_key=self.text_key) for row in csv_reader]
                
                if not all_rows:
                    self.status = "The CSV data is empty."
                    return []
                
                # Apply row slicing
                start_idx = self.start_index if self.start_index is not None else 0
                stop_idx = self.stop_index if self.stop_index is not None else len(all_rows)
                
                # Validate indices
                if start_idx < 0:
                    start_idx = max(0, len(all_rows) + start_idx)
                if stop_idx < 0:
                    stop_idx = max(0, len(all_rows) + stop_idx)
                
                # Ensure start_idx is not greater than stop_idx
                if start_idx > stop_idx:
                    self.status = f"Start index ({start_idx}) cannot be greater than stop index ({stop_idx})."
                    return []
                
                # Slice the data
                result = all_rows[start_idx:stop_idx]
                
                if not result:
                    self.status = f"No rows found in the specified range [{start_idx}:{stop_idx}]."
                    return []
                
                # self.status = f"Successfully loaded {len(result)} rows from index {start_idx} to {min(stop_idx, len(all_rows))}."
                self.status = result
                return result
                
        except csv.Error as e:
            error_message = f"CSV parsing error: {e}"
            self.status = error_message
            raise ValueError(error_message) from e
        except Exception as e:
            error_message = f"An error occurred: {e}"
            self.status = error_message
            raise ValueError(error_message) from e
        
        # An error occurred
        raise ValueError(self.status)



        you can use whatever u want see ef_2 for continuation 

        we are parsing

person details

icp

company_details

market

linkedin summary

champion scoring 

and the we are using this prompt



Create a personalized outreach message for a {channel} campaign targeting a prospect at a company where our product is a strong fit.

Use the following information:

Contact Info:

{contact_info}

Company Info:

{company_info}

ICP Assessment:

{icp_assesment}

Company Market Intelligence and Engagement Signals:

{market_engagement}

Product Context:

{product_context}

Tone of the message:

{preferred_tone}

LinkedIn Engagement Signal Summary:

{linkedin_posts_summary}

Champion Scoring Result:

{champion_scoring_result}

cehck ef_3.webp as well 

we are als parsing product fit for broucher switcher the code is this 


from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Data

class HiveProBothBrochure(Component):
    display_name = "Brochure Switcher"
    description = "Returns HTML block with inline CSS for Hive (Agent Hive), Pro, or Both brochure(s), displayed as direct links within a single section."  
    icon = "code"
    name = "HiveProBothBrochure"
    
    inputs = [
        MessageTextInput(
            name="input_text",
            display_name="Input Text",
            info="Enter 'Hive', 'Pro', or 'Both' (case-insensitive).",
            required=True,
        ),
    ]
    
    outputs = [
        Output(display_name="HTML Output", name="output", method="build_output"),
    ]
    
    def build_output(self) -> Message:
        def generate_brochure_html(product_type: str) -> str:
            brochure_links = {
                "Pro": "https://drive.google.com/file/d/1jrTEvbJwz-otvz8cJlNQDXh7g05vsx3r/view?usp=sharing",
                "Hive": "https://drive.google.com/file/d/1Hrlqff5_UjJ0gVpihKomr8eZpBbAQOH-/view?usp=sharing"
            }
            
            # SVG icon template
            svg_icon = '''<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="brochure-icon" style="margin: 0; padding: 0; box-sizing: border-box; width: 16px; height: 16px;"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/></svg>'''
            
            # Section container start
            section_start = '''<div class="brochure-section" style="margin: 0; padding: 0; box-sizing: border-box; margin: 32px 0; padding: 20px; background: linear-gradient(135deg, #f8f9ff 0%, #fff5f8 100%); border-radius: 8px; border-left: 4px solid rgb(204,43,156);">
                <div class="brochure-title" style="margin: 0; padding: 0; box-sizing: border-box; font-size: 15px; font-weight: 600; color: #1a1a1a; margin-bottom: 8px;">Learn More About Our Solutions</div>'''
            
            # Link template
            link_template = '''                <a href="{link}" class="brochure-link" style="margin: 0; padding: 0; box-sizing: border-box; color: rgb(204,43,156); text-decoration: none; font-weight: 500; display: inline-flex; align-items: center; gap: 6px; transition: color 0.2s ease;">
                    {svg_icon}
                    Download QpiAI {product} Brochure
                </a>'''
            
            section_end = '''            </div>'''
            
            p = product_type.strip().capitalize()
            if p not in ["Pro", "Hive", "Both"]:
                return "<!-- Invalid product type -->"
            
            # Determine which brochures to include
            items = [p] if p in ["Pro", "Hive"] else ["Pro", "Hive"]
            
            # Build links HTML
            links_html = ""
            for i, name in enumerate(items):
                display_name = name if name != "Hive" else "Agent Hive"
                links_html += link_template.format(
                    link=brochure_links[name], 
                    product=display_name,
                    svg_icon=svg_icon
                )
                # Add line break between links if there are multiple
                if i < len(items) - 1:
                    links_html += "\n                <br>\n"
            
            # Combine into single section
            return section_start + "\n" + links_html + "\n" + section_end
        
        html_output = generate_brochure_html(self.input_text)
        self.status = f"Generated brochure for: {self.input_text.strip().capitalize()}"
        return html_output

        personalized outreach content generation ef_4.webp

        and then finally we have a gmail composion tool 

and the prmoppt to our personalized outreach context generation is tour model or agent


You are an expert SDR tasked with creating the content for a Gmail outreach email.  
You will output exactly the sections below, in JSON.

1. subject: One-liner subject that highlights the value prop or outcome you're offering. Avoid generic phrases — instead, tease the benefit or the problem you solve. Example: 'Faster ML Model Deployment at Acme Inc'

2. greeting: Start with a friendly opener using the prospect’s first name (e.g., 'Hey Sam,' or 'Hi Dr. Lee,'). Keep it short and natural.

3. introduction: Write a warm intro that shows you've done your homework. Mention something specific about the prospect’s *role*, their *company*, or a *recent initiative* they’ve undertaken. Bonus: Mention any tech, tools, or trends they use if known. The tone should be professional yet human. Avoid sounding robotic.

4. pain_point: A sentence highlighting a challenge, friction point, or inefficiency the prospect or their team likely faces — ideally one related to their work or domain. Don’t overgeneralize. Use industry or role-specific language when possible.

5. product_desc : In 1–2 sentences, explain what the product does and how it directly solves the above pain. Keep it crisp and solution-focused. Use ***bold formatting*** for product names or standout features. Avoid jargon or vague buzzwords.

6. bullet_points:
  - Provide an array of 2–4 high-impact, skimmable benefits of the product. Focus on outcomes like increased efficiency, ROI, speed, or ease of use. Start each line with an emoji that matches the tone of the benefit. Use **bold** for stats or key results, *italics* for emphasis, and `monospace` only for tech terms.

7. cta: End with a short and specific line that encourages a response or meeting. Make it action-oriented (e.g., 'Open to a 15-min call this week?' or 'Should we explore if this fits your roadmap?'). Avoid pushy language.

AVAILABLE TEXT FORMATTING OPTIONS:
Use these markdown-style formats in your output:

1. **text** → Highlights important terms in pink color (rgb(204,43,156))
2. ***text*** → Bold highlights for extra emphasis 
3. *text* → Italic text for subtle emphasis
4. `text` → Inline code/technical terms in monospace

NOTE: 
Do NOT use these formatting in subject, greeting and CTA.

EXAMPLE LLM OUTPUT:
```json
{
  "subject": "Accelerate Visual Recognition at Acme Labs",
  "greeting": "Hey David,"
  "introduction": "Came across **Acme Labs** and your work in *visual recognition technology*, particularly the way you leverage `deep learning` models, really stood out.",
  "pain_point": "Building and deploying computer vision models often demands heavy coding and long development cycles.",
  "product_desc": "***QpiAI Pro*** lets teams build and deploy vision models without writing a single line of code.",
  "bullet_points": [
    "🚀 Speeds up development cycles by up to **50%**",
    "💵 Cuts engineering and infrastructure costs with *automated orchestration*",
    "⚙️ Empowers your engineers to use `QpiAI Pro` for faster iterations"
  ],
  "cta": "Worth a quick chat this week to see if this could streamline your next project?"
}
```

ADDITIONAL CONTEXT USAGE INSTRUCTION:

You may also be provided with the following additional context fields:

1. LinkedIn Engagement Signal Summary (Optional):

If available, use the engagement_signal_summary to:

- Personalize the introduction using core_themes, recent_focus, or example_opening_line.
- Adjust tone of the email to mirror their writing_style.
- Reference the best_personalization_angle to show relevance and build trust.

2. Champion Score (Optional):

Use the champion_score and reasoning to:

- If score ≥ 7, treat them as a high-fit champion — use a confident tone and direct CTA.
- If score between 4–6, keep the tone consultative and informative.
- If score < 4, keep it value-first, minimal pressure — CTA can be indirect or omitted.

The product_fit may be echoed for context alignment.


we also have a email text formatter 



from langflow.custom import Component
from langflow.io import MessageTextInput, Output, DataInput
from langflow.schema import Data
import json
import re

class EmailTextFormatter(Component):
    display_name = "Email Text Formatter"
    description = "Takes JSON email data and applies text formatting to specific fields (excludes subject, greeting, and cta)."  
    icon = "edit"
    name = "EmailTextFormatter"
    
    inputs = [
        DataInput(
            name="json_input",
            display_name="JSON Input",
            info="Enter JSON object with email fields (subject, greeting, introduction, pain_point, product_desc, bullet_points, cta).",
            required=True,
        ),
    ]
    
    outputs = [
        Output(display_name="Formatted JSON", name="output", method="build_output"),
    ]
    
    def format_email_text(self, text, replacements=None):
        """Apply text formatting to email content"""
        if not text:
            return ''
        
        if replacements is None:
            replacements = {}
        
        formatted_text = text
        
        # Apply placeholder replacements first (if any)
        for key, value in replacements.items():
            regex = re.compile(rf'\[{re.escape(key)}\]')
            formatted_text = regex.sub(value, formatted_text)
        
        # Apply text formatting
        # Triple asterisks (***text***) → Bold highlights
        formatted_text = re.sub(
            r'\*\*\*(.*?)\*\*\*',
            r'<span style="margin: 0; padding: 0; box-sizing: border-box; color: rgb(204,43,156); font-weight: 600;">\1</span>',
            formatted_text
        )
        
        # Double asterisks (**text**) → Regular highlights  
        formatted_text = re.sub(
            r'\*\*(.*?)\*\*',
            r'<span style="margin: 0; padding: 0; box-sizing: border-box; color: rgb(204,43,156); font-weight: 500;">\1</span>',
            formatted_text
        )
        
        # Single asterisks (*text*) → Italic
        formatted_text = re.sub(
            r'\*(.*?)\*',
            r'<em style="margin: 0; padding: 0; box-sizing: border-box;">\1</em>',
            formatted_text
        )
        
        # Backticks (`text`) → Inline code
        formatted_text = re.sub(
            r'`(.*?)`',
            r'<code style="margin: 0; padding: 0; box-sizing: border-box; background: #f1f3f4; padding: 2px 4px; border-radius: 3px; font-family: monospace; font-size: 14px;">\1</code>',
            formatted_text
        )
        
        return formatted_text
    
    def build_output(self) -> Message:
        try:
            # Parse the JSON input
            email_data = self.json_input.data
            
            # Fields to exclude from formatting
            exclude_fields = {'subject', 'greeting', 'cta'}
            
            # Create a copy of the original data
            formatted_data = email_data.copy()
            
            # Apply formatting to all fields except excluded ones
            for field, value in email_data.items():
                if field not in exclude_fields:
                    if isinstance(value, str):
                        # Format string fields
                        formatted_data[field] = self.format_email_text(value)
                    elif isinstance(value, list):
                        # Format list items (like bullet_points)
                        formatted_data[field] = [
                            self.format_email_text(item) if isinstance(item, str) else item
                            for item in value
                        ]
            
            # Convert back to JSON string with proper formatting
            formatted_json = json.dumps(formatted_data, indent=2, ensure_ascii=False)
            
            self.status = f"Successfully formatted email text for {len([k for k in email_data.keys() if k not in exclude_fields])} fields"
            return formatted_json
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON input: {str(e)}"
            self.status = error_msg
            return json.dumps({"error": error_msg}, indent=2)
        except Exception as e:
            error_msg = f"Error processing email data: {str(e)}"
            self.status = error_msg
            return json.dumps({"error": error_msg}, indent=2)


            and this we are giving to bullet point html generator  and also json field extractor 



            
from langflow.custom import Component
from langflow.io import MessageTextInput, Output
from langflow.schema import Data
import json
import re

class BulletPointsHTMLGenerator(Component):
    display_name = "Bullet Points HTML Generator"
    description = "Takes JSON email data and generates HTML bullet points with custom styling from the bullet_points field."  
    icon = "list"
    name = "BulletPointsHTMLGenerator"
    
    inputs = [
        MessageTextInput(
            name="json_input",
            display_name="JSON Input",
            info="Enter the full JSON object with email fields. Will extract bullet_points field and generate HTML.",
            required=True,
        ),
    ]
    
    outputs = [
        Output(display_name="HTML Output", name="output", method="build_output"),
    ]
    
    def format_email_text(self, text, replacements=None):
        """Apply text formatting to email content"""
        if not text:
            return ''
        
        if replacements is None:
            replacements = {}
        
        formatted_text = text
        
        # Apply placeholder replacements first (if any)
        for key, value in replacements.items():
            regex = re.compile(rf'\[{re.escape(key)}\]')
            formatted_text = regex.sub(value, formatted_text)
        
        # Apply text formatting
        # Triple asterisks (***text***) → Bold highlights
        formatted_text = re.sub(
            r'\*\*\*(.*?)\*\*\*',
            r'<span style="margin: 0; padding: 0; box-sizing: border-box; color: rgb(204,43,156); font-weight: 600;">\1</span>',
            formatted_text
        )
        
        # Double asterisks (**text**) → Regular highlights  
        formatted_text = re.sub(
            r'\*\*(.*?)\*\*',
            r'<span style="margin: 0; padding: 0; box-sizing: border-box; color: rgb(204,43,156); font-weight: 500;">\1</span>',
            formatted_text
        )
        
        # Single asterisks (*text*) → Italic
        formatted_text = re.sub(
            r'\*(.*?)\*',
            r'<em style="margin: 0; padding: 0; box-sizing: border-box;">\1</em>',
            formatted_text
        )
        
        # Backticks (`text`) → Inline code
        formatted_text = re.sub(
            r'`(.*?)`',
            r'<code style="margin: 0; padding: 0; box-sizing: border-box; background: #f1f3f4; padding: 2px 4px; border-radius: 3px; font-family: monospace; font-size: 14px;">\1</code>',
            formatted_text
        )
        
        return formatted_text
    
    def generate_bullet_points(self, bullet_points=None):
        """Generate bullet points HTML with inline CSS"""
        if not bullet_points or len(bullet_points) == 0:
            return ''
        
        # Format each bullet point text and create list items
        bullet_items = []
        for bullet_text in bullet_points:
            # Apply text formatting to the bullet text
            # formatted_text = self.format_email_text(bullet_text)
            formatted_text = bullet_text
            
            bullet_item = f'''        <li class="benefit-item" style="margin: 0; padding: 0; box-sizing: border-box; display: flex; align-items: flex-start; margin: 16px 0; padding: 0;">
            <div class="benefit-bullet" style="margin: 0; padding: 0; box-sizing: border-box; width: 6px; height: 6px; background-color: rgb(140,172,228); border-radius: 50%; margin-top: 10px; margin-right: 12px; flex-shrink: 0;"></div>
            <div class="benefit-text" style="margin: 0; padding: 0; box-sizing: border-box; flex: 1; font-size: 15px; line-height: 1.6; color: #333333;">{formatted_text}</div>
        </li>'''
            bullet_items.append(bullet_item)
        
        bullet_items_html = '\n'.join(bullet_items)
        
        return f'''    <ul class="benefits-list" style="margin: 0; padding: 0; box-sizing: border-box; margin: 0; padding: 0; list-style: none;">
{bullet_items_html}
    </ul>'''
    
    def build_output(self) -> Message:
        try:
            # Parse the JSON input
            email_data = json.loads(self.json_input)
            
            # Extract bullet_points field
            bullet_points = email_data.get('bullet_points', [])
            
            if not bullet_points:
                self.status = "No bullet_points field found or empty"
                return "<!-- No bullet points to display -->"
            
            # Generate HTML bullet points
            html_output = self.generate_bullet_points(bullet_points)
            
            self.status = f"Generated HTML for {len(bullet_points)} bullet points"
            return html_output
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON input: {str(e)}"
            self.status = error_msg
            return f"<!-- {error_msg} -->"
        except Exception as e:
            error_msg = f"Error processing bullet points: {str(e)}"
            self.status = error_msg
            return f"<!-- {error_msg} -->"


and these things we are sention to a pmrpt which is this 




<body style="margin: 0; padding: 0; box-sizing: border-box; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #1a1a1a; background-color: #f8f9fa; padding: 20px 0;">
    <div class="email-container" style="margin: 0; padding: 0; box-sizing: border-box; max-width: 600px; margin: 0 auto; background: #ffffff; border: 1px solid #e9ecef; border-radius: 8px; overflow: hidden; position: relative;">
 
        <div class="content" style="margin: 0; padding: 0; box-sizing: border-box; padding: 40px; position: relative; z-index: 2;">
            <div class="greeting" style="margin: 0; padding: 0; box-sizing: border-box; font-size: 16px; color: #1a1a1a; margin-bottom: 24px; font-weight: 500;">
                {GREETING}
            </div>

            <!-- Introduction -->
            <div class="paragraph" style="margin: 0; padding: 0; box-sizing: border-box; margin-bottom: 24px; font-size: 15px; line-height: 1.7; color: #333333;">
                {INTRODUCTION}
            </div>

            <!-- Pain Point -->
            <div class="paragraph" style="margin: 0; padding: 0; box-sizing: border-box; margin-bottom: 24px; font-size: 15px; line-height: 1.7; color: #333333;">
             {PAIN_POINT}
            </div>

            <!-- Product Section -->
            <div class="product-section" style="margin: 0; padding: 0; box-sizing: border-box; margin: 32px 0;">
                <div class="product-intro" style="margin: 0; padding: 0; box-sizing: border-box; font-size: 15px; line-height: 1.7; color: #333333; margin-bottom: 20px;">
                    {PRODUCT_DESC}
                </div>

                {BENEFITS_HTML}
            </div>

            <!-- Brochure Section -->
            {BROCHURE_SECTION_HTML}

            <!-- CTA Section -->
            <div class="cta-section" style="margin: 0; padding: 0; box-sizing: border-box; margin-top: 40px; padding-top: 32px; border-top: 1px solid #f1f3f4;">
                <div class="cta-text" style="margin: 0; padding: 0; box-sizing: border-box; font-size: 16px; font-weight: 600; color: rgb(204,43,156); margin-bottom: 8px;">{CTA}</div>
                <!-- <div class="cta-description" style="margin: 0; padding: 0; box-sizing: border-box; font-size: 14px; color: #666666; line-height: 1.5;">Worth a quick chat this week to see if this could streamline your next project?</div> -->
            </div>

        <div class="footer" style="margin: 0; padding: 0; box-sizing: border-box; background-color: #f8f9fa; padding: 20px 40px; text-align: center; font-size: 12px; color: #666666; border-top: 1px solid #f1f3f4; position: relative; z-index: 2;">
            <a href="https://qpiai.tech" style="margin: 0; padding: 0; box-sizing: border-box; color: rgb(140,172,228); text-decoration: none;">QpiAI.tech</a>
        </div>
    </div>
</body>


and its begin used by composio tool in body  and we are taking subject from json field extractor 

and this is the code for tje composio tool


import json
from typing import Any

from composio import Action

from langflow.base.composio.composio_base import ComposioBaseComponent
from langflow.inputs.inputs import (
    BoolInput,
    FileInput,
    IntInput,
    MessageTextInput,
)
from langflow.logging import logger


class ComposioGmailAPIComponent(ComposioBaseComponent):
    """Gmail API component for interacting with Gmail services."""

    display_name: str = "Gmail"
    name = "GmailAPI"
    icon = "Google"
    documentation: str = "https://docs.composio.dev"
    app_name = "gmail"

    # Gmail-specific actions
    _actions_data: dict = {
        "GMAIL_SEND_EMAIL": {
            "display_name": "Send Email",
            "action_fields": [
                "recipient_email",
                "subject",
                "body",
                "cc",
                "bcc",
                "is_html",
                "gmail_user_id",
                "attachment",
            ],
        },
        "GMAIL_FETCH_EMAILS": {
            "display_name": "Fetch Emails",
            "action_fields": [
                "gmail_user_id",
                "max_results",
                "query",
                "page_token",
                "label_ids",
                "include_spam_trash",
            ],
            "get_result_field": True,
            "result_field": "messages",
        },
        "GMAIL_GET_PROFILE": {
            "display_name": "Get User Profile",
            "action_fields": ["gmail_user_id"],
        },
        "GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID": {
            "display_name": "Get Email By ID",
            "action_fields": ["message_id", "gmail_user_id", "format"],
            "get_result_field": False,
        },
        "GMAIL_CREATE_EMAIL_DRAFT": {
            "display_name": "Create Draft Email",
            "action_fields": [
                "recipient_email",
                "subject",
                "body",
                "cc",
                "bcc",
                "is_html",
                "attachment",
                "gmail_user_id",
            ],
        },
        "GMAIL_FETCH_MESSAGE_BY_THREAD_ID": {
            "display_name": "Get Message By Thread ID",
            "action_fields": ["thread_id", "page_token", "gmail_user_id"],
            "get_result_field": False,
        },
        "GMAIL_LIST_THREADS": {
            "display_name": "List Email Threads",
            "action_fields": ["max_results", "query", "gmail_user_id", "page_token"],
            "get_result_field": True,
            "result_field": "threads",
        },
        "GMAIL_REPLY_TO_THREAD": {
            "display_name": "Reply To Thread",
            "action_fields": ["thread_id", "message_body", "recipient_email", "gmail_user_id", "cc", "bcc", "is_html"],
        },
        "GMAIL_LIST_LABELS": {
            "display_name": "List Email Labels",
            "action_fields": ["gmail_user_id"],
            "get_result_field": True,
            "result_field": "labels",
        },
        "GMAIL_CREATE_LABEL": {
            "display_name": "Create Email Label",
            "action_fields": ["label_name", "label_list_visibility", "message_list_visibility", "gmail_user_id"],
        },
        "GMAIL_GET_PEOPLE": {
            "display_name": "Get Contacts",
            "action_fields": ["resource_name", "person_fields"],
            "get_result_field": True,
            "result_field": "people_data",
        },
        "GMAIL_REMOVE_LABEL": {
            "display_name": "Delete Email Label",
            "action_fields": ["label_id", "gmail_user_id"],
            "get_result_field": False,
        },
        "GMAIL_GET_ATTACHMENT": {
            "display_name": "Get Attachment",
            "action_fields": ["message_id", "attachment_id", "file_name", "gmail_user_id"],
        },
    }
    _all_fields = {field for action_data in _actions_data.values() for field in action_data["action_fields"]}
    _bool_variables = {"is_html", "include_spam_trash"}

    # Combine base inputs with Gmail-specific inputs
    inputs = [
        *ComposioBaseComponent._base_inputs,
        # Email composition fields
        MessageTextInput(
            name="recipient_email",
            display_name="Recipient Email",
            info="Email address of the recipient",
            show=False,
            required=True,
            advanced=False,
        ),
        MessageTextInput(
            name="subject",
            display_name="Subject",
            info="Subject of the email",
            show=False,
            required=True,
            advanced=False,
        ),
        MessageTextInput(
            name="body",
            display_name="Body",
            required=True,
            info="Content of the email",
            show=False,
            advanced=False,
        ),
        MessageTextInput(
            name="cc",
            display_name="CC",
            info="Email addresses to CC (Carbon Copy) in the email, separated by commas",
            show=False,
            advanced=True,
        ),
        MessageTextInput(
            name="bcc",
            display_name="BCC",
            info="Email addresses to BCC (Blind Carbon Copy) in the email, separated by commas",
            show=False,
            advanced=True,
        ),
        BoolInput(
            name="is_html",
            display_name="Is HTML",
            info="Specify whether the email body contains HTML content (true/false)",
            show=False,
            value=False,
            advanced=True,
        ),
        # Email retrieval and management fields
        MessageTextInput(
            name="gmail_user_id",
            display_name="User ID",
            info="The user's email address or 'me' for the authenticated user",
            show=False,
            advanced=True,
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            required=True,
            info="Maximum number of emails to be returned",
            show=False,
            advanced=False,
        ),
        MessageTextInput(
            name="message_id",
            display_name="Message ID",
            info="The ID of the specific email message",
            show=False,
            required=True,
            advanced=False,
        ),
        MessageTextInput(
            name="thread_id",
            display_name="Thread ID",
            info="The ID of the email thread",
            show=False,
            required=True,
            advanced=False,
        ),
        MessageTextInput(
            name="query",
            display_name="Query",
            info="Search query to filter emails (e.g., 'from:someone@email.com' or 'subject:hello')",
            show=False,
            advanced=False,
        ),
        MessageTextInput(
            name="message_body",
            display_name="Message Body",
            info="The body content of the message to be sent",
            show=False,
            advanced=True,
        ),
        # Label management fields
        MessageTextInput(
            name="label_name",
            display_name="Label Name",
            info="Name of the Gmail label to create, modify, or filter by",
            show=False,
            required=True,
            advanced=False,
        ),
        MessageTextInput(
            name="label_id",
            display_name="Label ID",
            info="The ID of the Gmail label",
            show=False,
            advanced=False,
        ),
        MessageTextInput(
            name="label_ids",
            display_name="Label Ids",
            info="Comma-separated list of label IDs to filter messages",
            show=False,
            advanced=True,
        ),
        MessageTextInput(
            name="label_list_visibility",
            display_name="Label List Visibility",
            info="The visibility of the label in the label list in the Gmail web interface",
            show=False,
            advanced=True,
        ),
        MessageTextInput(
            name="message_list_visibility",
            display_name="Message List Visibility",
            info="The visibility of the label in the message list in the Gmail web interface",
            show=False,
            advanced=True,
        ),
        # Pagination and filtering
        MessageTextInput(
            name="page_token",
            display_name="Page Token",
            info="Token for retrieving the next page of results",
            show=False,
            advanced=True,
        ),
        BoolInput(
            name="include_spam_trash",
            display_name="Include messages from Spam/Trash",
            info="Include messages from SPAM and TRASH in the results",
            show=False,
            value=False,
            advanced=True,
        ),
        MessageTextInput(
            name="format",
            display_name="Format",
            info="The format to return the message in. Possible values: minimal, full, raw, metadata",
            show=False,
            advanced=True,
        ),
        # Contact management fields
        MessageTextInput(
            name="resource_name",
            display_name="Resource Name",
            info="The resource name of the person to provide information about",
            show=False,
            advanced=True,
        ),
        MessageTextInput(
            name="person_fields",
            display_name="Person fields",
            info="Fields to return for the person. Multiple fields can be specified by separating them with commas",
            show=False,
            advanced=True,
        ),
        # Attachment handling
        MessageTextInput(
            name="attachment_id",
            display_name="Attachment ID",
            info="Id of the attachment",
            show=False,
            required=True,
            advanced=False,
        ),
        MessageTextInput(
            name="file_name",
            display_name="File name",
            info="File name of the attachment file",
            show=False,
            required=True,
            advanced=False,
        ),
        FileInput(
            name="attachment",
            display_name="Add Attachment",
            file_types=[
                "csv",
                "txt",
                "doc",
                "docx",
                "xls",
                "xlsx",
                "pdf",
                "png",
                "jpg",
                "jpeg",
                "gif",
                "zip",
                "rar",
                "ppt",
                "pptx",
            ],
            info="Add an attachment",
            show=False,
        ),
    ]

    def execute_action(self):
        """Execute action and return response as Message."""
        toolset = self._build_wrapper()

        try:
            self._build_action_maps()
            # Get the display name from the action list
            display_name = self.action[0]["name"] if isinstance(self.action, list) and self.action else self.action
            # Use the display_to_key_map to get the action key
            action_key = self._display_to_key_map.get(display_name)
            if not action_key:
                msg = f"Invalid action: {display_name}"
                raise ValueError(msg)

            enum_name = getattr(Action, action_key)
            params = {}
            if action_key in self._actions_data:
                for field in self._actions_data[action_key]["action_fields"]:
                    value = getattr(self, field)

                    if value is None or value == "":
                        continue

                    if field in ["cc", "bcc", "label_ids"] and value:
                        value = [item.strip() for item in value.split(",")]

                    if field in self._bool_variables:
                        value = bool(value)

                    params[field] = value

            if params.get("gmail_user_id"):
                params["user_id"] = params.pop("gmail_user_id")

            result = toolset.execute_action(
                action=enum_name,
                params=params,
            )
            if not result.get("successful"):
                message_str = result.get("data", {}).get("message", "{}")
                try:
                    error_data = json.loads(message_str).get("error", {})
                except json.JSONDecodeError:
                    error_data = {"error": "Failed to get exact error details"}
                return {
                    "code": error_data.get("code"),
                    "message": error_data.get("message"),
                    "errors": error_data.get("errors", []),
                    "status": error_data.get("status"),
                }

            result_data = result.get("data", {})
            actions_data = self._actions_data.get(action_key, {})
            # If 'get_result_field' is True and 'result_field' is specified, extract the data
            # using 'result_field'. Otherwise, fall back to the entire 'data' field in the response.
            if actions_data.get("get_result_field") and actions_data.get("result_field"):
                result_data = result_data.get(actions_data.get("result_field"), result.get("data", []))
            if len(result_data) != 1 and not actions_data.get("result_field") and actions_data.get("get_result_field"):
                msg = f"Expected a dict with a single key, got {len(result_data)} keys: {result_data.keys()}"
                raise ValueError(msg)
            return result_data  # noqa: TRY300
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            display_name = self.action[0]["name"] if isinstance(self.action, list) and self.action else str(self.action)
            msg = f"Failed to execute {display_name}: {e!s}"
            raise ValueError(msg) from e

    def update_build_config(self, build_config: dict, field_value: Any, field_name: str | None = None) -> dict:
        return super().update_build_config(build_config, field_value, field_name)

    def set_default_tools(self):
        self._default_tools = {
            "GMAIL_SEND_EMAIL",
            "GMAIL_FETCH_EMAILS",
        }

adm cjheckl ef_5.webp for the final composio call and everythingg

