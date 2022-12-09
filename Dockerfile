FROM python:3.10.8

WORKDIR /app

COPY . .

# Install pipenv
RUN pip install pipenv && \
    pipenv install

# Mount the .env file from the data volume container to the container
#VOLUME /chatgpt-telegram-bot/.env

# Run the main.py file
CMD "pipenv", "run", "python", "main.py"