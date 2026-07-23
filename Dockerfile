FROM photo-transform-api:latest
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir itsdangerous
COPY app /app/app
COPY static /app/static
COPY data /app/data
COPY .env /app/.env
ENV HOST=0.0.0.0 PORT=8781
EXPOSE 8781
CMD ["python", "-m", "app.main"]
