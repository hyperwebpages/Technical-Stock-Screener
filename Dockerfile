FROM python:3.8

RUN echo 'alias ll="ls -al"' >> ~/.bashrc

COPY . /app/
WORKDIR /app

RUN pip3 install -r requirements.txt
RUN pip3 install --editable .

ENTRYPOINT ["streamlit", "run", "app/main.py", "--server.port=8501"]
