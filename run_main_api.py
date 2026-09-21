"""Start API against MAIN DB (medivo_qa via tunnel). Run: python run_main_api.py"""
import os

os.environ["DB_HOST"] = "127.0.0.1"
os.environ["DB_PORT"] = "5438"
os.environ["DB_DATABASE"] = "medivo_qa"
os.environ["DB_USERNAME"] = "postgres"
os.environ["DB_PASSWORD"] = "q4$TK8((rq0e!XD9n9T.kj~_:mc$"

import uvicorn

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8093)
