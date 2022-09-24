FROM python:3.9-slim

RUN echo 'alias ll="ls -al"' >> ~/.bashrc

# TA-Lib
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xvzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install
RUN rm -R ta-lib ta-lib-0.4.0-src.tar.gz

COPY . /app/
WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501"]
