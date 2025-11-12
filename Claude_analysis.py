import base64
from botocore.config import Config
from io import BytesIO
import boto3, re, json, os
from dotenv import load_dotenv
import markdown

load_dotenv()


def get_claude_analysis(masterJSON, docJSON):
    client = boto3.client(
        "bedrock-runtime",
        region_name=os.getenv("AWS_REGION"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )

    prompt = (
        f"{list(masterJSON.keys())[0]} is the master file or the product order file. "
        f"The rest of the {len(docJSON)} files are the Delivery Chalans of {len(docJSON)} orders "
        f"from the {list(masterJSON.keys())[0]}. "
        f"Identify which Delivery Chalan corresponds to which item in the PO, "
        f"and then find and describe the discrepancies among the {len(docJSON)} DC OCR text outputs."
    )

    system_prompts = [
        {
            "text": (
                "You are a meticulous supply chain data analyst. "
                "You will be given one product order (PO) OCR text and multiple delivery chalan (DC) using information in OCR extracted text. "
                "Match each DC to the correct PO item(s) and report any discrepancies "
                "in quantities, item descriptions, or missing items. "
                "Use HTML tags like <h1>, <h2>, <p>, <b>, <ul>, <li>, <table>, etc. for formatting your response to make it more readable in webpage."
                "Highlight discrepancies using <span style='color:red;'> for missing items or wrong quantities. "
                "Highlight correct matches using <span style='color:green;'>. "
                "Do NOT use any markdown formatting. Strictly use html formatting for the response."
            )
        }
    ]

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "text": prompt + "\n\n"
                    f"---\nMaster PO JSON:\n{masterJSON}\n\n"
                    f"---\nDelivery Chalan JSON List:\n{docJSON}"
                }
            ],
        }
    ]

    model_response = client.converse(
        modelId=os.getenv("BEDROCK_LLM_MODEL_ID"),
        messages=messages,
        system=system_prompts,
        inferenceConfig={
            "maxTokens": 4096,
            "temperature": 0.2,
        },
    )

    try:
        output_text = model_response["output"]["message"]["content"][0]["text"]
    except Exception:
        output_text = str(model_response)

    return output_text


# with open(
#     "/Users/sohampaul/Desktop/Programming Languages/OCR_Project3/get_json/comparison_results1/PO.json",
#     "rb",
# ) as f:
#     po_json = f.read()

# masterJSON = {"PO.json": po_json}
# docJSON = []

# with open(
#     "/Users/sohampaul/Desktop/Programming Languages/OCR_Project3/get_json/comparison_results1/DC-6.json",
#     "rb",
# ) as f:
#     do6_json = f.read()

# docJSON.append({"DC-6.json": do6_json})

# with open(
#     "/Users/sohampaul/Desktop/Programming Languages/OCR_Project3/get_json/comparison_results1/DC-7.json",
#     "rb",
# ) as f:
#     do7_json = f.read()

# docJSON.append({"DC-7.json": do7_json})

# markdown_text = get_claude_analysis(masterJSON=masterJSON, docJSON=docJSON)
# html_output = markdown.markdown(markdown_text)
# print(markdown_text)
# print(html_output)
