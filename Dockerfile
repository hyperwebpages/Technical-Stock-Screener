FROM python:3.9-slim

EXPOSE 8501

WORKDIR /app
COPY . /app

RUN apt-get update
RUN pip3 install -r requirements.txt

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
