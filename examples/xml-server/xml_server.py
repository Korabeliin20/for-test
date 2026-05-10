import xml.etree.ElementTree as ET
from datetime import datetime

from fastapi import FastAPI, Request, Response

app = FastAPI()

# Data storage
orders = []


@app.post("/api/xml/simple")
async def receive_simple_xml(request: Request):
    """Simple endpoint for receiving XML"""
    body = await request.body()
    return Response(content=body, media_type="application/xml")


@app.post("/api/xml/order")
async def create_order(request: Request):
    """Endpoint for creating orders with nested structure"""
    body = await request.body()

    # Parse XML
    root = ET.fromstring(body.decode("utf-8"))

    # Extract data
    order_id = root.find("id").text if root.find("id") is not None else "1"
    customer = (
        root.find("customer/name").text
        if root.find("customer/name") is not None
        else "Unknown"
    )

    # Create response
    response_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<orderResponse>
    <id>{order_id}</id>
    <status>created</status>
    <timestamp>{datetime.now().isoformat()}</timestamp>
    <customer>
        <name>{customer}</name>
        <message>Order received successfully</message>
    </customer>
</orderResponse>"""

    orders.append({"id": order_id, "customer": customer})
    return Response(content=response_xml, media_type="application/xml")


@app.get("/api/xml/orders")
async def get_orders():
    """Endpoint for getting orders list in XML"""
    orders_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<orders>'

    for order in orders:
        orders_xml += f"""
    <order>
        <id>{order["id"]}</id>
        <customer>
            <name>{order["customer"]}</name>
        </customer>
    </order>"""

    orders_xml += "\n</orders>"
    return Response(content=orders_xml, media_type="application/xml")


@app.get("/api/xml/nested")
async def get_nested_xml():
    """Endpoint with deeply nested XML structure"""
    nested_xml = """<?xml version="1.0" encoding="UTF-8"?>
<company>
    <name>TechCorp</name>
    <departments>
        <department id="1">
            <name>Engineering</name>
            <employees>
                <employee>
                    <id>101</id>
                    <name>John Doe</name>
                    <position>Senior Developer</position>
                    <skills>
                        <skill>Python</skill>
                        <skill>FastAPI</skill>
                        <skill>XML</skill>
                    </skills>
                </employee>
                <employee>
                    <id>102</id>
                    <name>Jane Smith</name>
                    <position>QA Engineer</position>
                    <skills>
                        <skill>Testing</skill>
                        <skill>Automation</skill>
                    </skills>
                </employee>
            </employees>
        </department>
        <department id="2">
            <name>Sales</name>
            <employees>
                <employee>
                    <id>201</id>
                    <name>Bob Johnson</name>
                    <position>Sales Manager</position>
                </employee>
            </employees>
        </department>
    </departments>
</company>"""

    return Response(content=nested_xml, media_type="application/xml")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
