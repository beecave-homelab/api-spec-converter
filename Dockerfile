FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install opdm
RUN pdm install

CMD ["python", "api_spec_converter/cli.py"]