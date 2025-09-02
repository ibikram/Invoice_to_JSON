from google.cloud import documentai
from google.api_core.client_options import ClientOptions
import os, time
from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "g-ocr-creds.json"
)


def process_document_sample(pdf_bytes: bytes):
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    processor_id = os.getenv("PROCESSOR_ID")
    mime_type = "application/pdf"
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = f"projects/{project_id}/locations/{location}/processors/{processor_id}"

    raw_document = documentai.RawDocument(content=pdf_bytes, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)

    data = result.document
    result = {}

    # FOR LINE ITEMS
    result["line_items"] = []

    # FOR TAXES
    result["taxes"] = []

    entities = data.entities
    for entity in entities:
        field = entity.type_
        if field == "billing_items":

            # print("===========ITEMS============TIMES=====================")
            item_dict = {}

            for property in entity.properties:
                # print(f"Item :\nID : {property.id}")
                field = property.type_
                text = property.mention_text
                conf = property.confidence

                # Putting in dict
                item_dict[field] = {"value": text, "conf": conf}

                # print(f"{field} : {text}\nConfidence : {conf}\n")

            result["line_items"].append(item_dict)

        elif field == "taxes":

            # print("===========TAXES============TIMES=====================")
            taxes_dict = {}

            for property in entity.properties:
                # print(f"Item :\nID : {property.id}")
                field = property.type_
                text = property.mention_text
                conf = property.confidence

                # Putting in dict
                taxes_dict[field] = {"value": text, "conf": conf}

                # print(f"{field} : {text}\nConfidence : {conf}\n")

            result["taxes"].append(taxes_dict)

        else:
            text = entity.mention_text
            conf = entity.confidence
            id_ = entity.id

            # Putting in dict
            result[field] = {}
            result[field]["value"] = text
            result[field]["conf"] = conf

            # print(f"{field} : {text} \nConfidence : {conf}\nID : {id_}\n")

    return result


# with open("/Users/sohampaul/Downloads/PO.pdf", "rb") as f:
#     pdf_data = f.read()

# st = time.time()
# result = process_document_sample(
#     pdf_bytes=pdf_data,
# )
# et = time.time()
# print(result)
# print("Total Time : ", et - st)
