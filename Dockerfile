FROM python:3.10.8
EXPOSE 8080

WORKDIR /app

COPY . .

# Install pipenv
RUN pip install -U pipenv && \
    pipenv install

# Run the main.py file
CMD ["bash", "start.sh"]
