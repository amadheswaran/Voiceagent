from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "AI Voice Agent is running on Vercel!"}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    # Call your chatbot logic here
    bot_response = f"You said: {user_input}"
    return JSONResponse({"response": bot_response})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
