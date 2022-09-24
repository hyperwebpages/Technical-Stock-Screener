FROM python:3.8

RUN echo 'alias ll="ls -al"' >> ~/.bashrc

COPY . /app/
WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
