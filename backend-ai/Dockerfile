FROM python:3.12-slim

WORKDIR /app

# libgl1/libglib2.0-0: paddleocr pulls in opencv-contrib-python (not
# the headless variant) via paddlex, which dlopen()s libGL at import
# time even though this service never renders anything to a display —
# without these, `import paddleocr` fails with
# "ImportError: libGL.so.1: cannot open shared object file".
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
