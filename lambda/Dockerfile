# Use AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.12

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements file (build context should be from project root)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY lambda/app.py .

# Set the CMD to your handler
CMD [ "app.handler" ]

