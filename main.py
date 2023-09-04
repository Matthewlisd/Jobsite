import os
import mysql.connector
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from dotenv import load_dotenv  # pip install python-dotenv
import torch
from torch.nn.functional import cosine_similarity
from transformers import BertTokenizer, BertModel
from datetime import date as DATE


#Import pretrained BERT
tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
model = BertModel.from_pretrained('bert-base-uncased')


PORT = 587
EMAIL_SERVER = "smtp-mail.outlook.com"  # Adjust server address, if you are not using @outlook

# Load the environment variables
current_dir = Path(__file__).resolve().parent if "__file__" in locals() else Path.cwd()
envars = current_dir / ".env"
load_dotenv(envars)

# Read environment variables
sender_email = os.getenv("email")
password_email = os.getenv("password")
db_host = os.getenv("db_host")
db_user = os.getenv("db_user")
db_password = os.getenv("db_password")
db_database = os.getenv("db_database")

connection = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_database
    )
#GET USERS AND JOBS to create embedding
#GET USERS FROM SQL DATABASE
if connection.is_connected():
        mycursor = connection.cursor()
        #print("Connected to the database.")

        #Find User id, Details from users
        '''
        mycursor.execute("SELECT id, email, Details FROM smartend_users")

        CV_Details = mycursor.fetchall()

        #Find unique user id, skills, years and level from database
        mycursor.execute("SELECT Id, UserId, Skill, Years, Level FROM smartend_mbamade_skills")
        Skills = mycursor.fetchall()
        '''
        mycursor.execute("Select smartend_users.email, smartend_mbamade_skills.Skill, smartend_mbamade_skills.Years, smartend_mbamade_skills.Level FROM smartend_users INNER JOIN smartend_mbamade_skills ON smartend_mbamade_skills.UserId = smartend_users.id")
        user_profiles = mycursor.fetchall()

#Set up today's date for email sending
TODAY = DATE.today()
AMERICAN_DATE = TODAY.strftime("%B %d, %Y")

#Test for USER shit
user_profiles = ["USER SKILLS EXPERIENCES HERE"]

#GET JOB_QUALIFICATIONS from MONGODB

job_qualifications = ["Take from MONGODB"]
# Convert descriptions to embeddings
user_emails = []
user_embeddings = []
job_embeddings = []

for profile in user_profiles:
    encoded_input = tokenizer(profile, return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        output = model(**encoded_input)
        user_embeddings.append(output.last_hidden_state[0, 0, :])

for job in job_qualifications:
    encoded_input = tokenizer(job, return_tensors='pt', padding=True, truncation=True)
    with torch.no_grad():
        output = model(**encoded_input)
        job_embeddings.append(output.last_hidden_state[0, 0, :])

# Convert lists of tensors to 2D tensors for similarity computation
user_embeddings = torch.stack(user_embeddings)
job_embeddings = torch.stack(job_embeddings)

# Compute recommendations for each user
num_recommendations = min(5, len(job_qualifications))
recommendations = {}

for i, user_embed in enumerate(user_embeddings):
    # Using unsqueeze to get shape (1, embedding_dim) for the user_embed tensor
    similarities = [cosine_similarity(user_embed.unsqueeze(0), job_embed.unsqueeze(0)) for job_embed in job_embeddings]
    
    # Sort jobs by similarity
    _, indices = torch.topk(torch.tensor(similarities), num_recommendations)
    
    recommendations[user_profiles[i]] = [job_qualifications[j] for j in indices.numpy()]

    print(recommendations)


####

#Compile Email that sends out the recommendatations
def send_email(subject, receiver_email, name, date, recommendations):
    # Create the base text message.
    msg = EmailMessage()
    msg["Subject"] = subject
    Tilte = "Your Job Recommendations for " + 
    msg["From"] = formataddr(("Your Job Recommendations for ", f"{sender_email}"))
    msg["To"] = receiver_email
    msg["BCC"] = sender_email

    msg.set_content(
        f"""\
        Hi {name},
        I hope you are well.
        
        Matthew Li
        """
    )
    # Add the html version.  This converts the message into a multipart/alternative
    # container, with the original text message as the first part and the new html
    # message as the second part.
    msg.add_alternative(
        f"""\
    <html>
      <body>
        <p>Hi {name},</p>
        <p>I hope you are well.<p>
        <p>Best regards</p>
        <p>Matthew Li</p>
      </body>
    </html>
    """,
        subtype="html",
    )

    with smtplib.SMTP(EMAIL_SERVER, PORT) as server:
        server.starttls()
        server.login(sender_email, password_email)
        server.sendmail(sender_email, receiver_email, msg.as_string())


if __name__ == "__main__":
    
    send_email(
        subject="Your Job Recommnedations",
        name="Maththew",
        receiver_email="matthewlisd@gmail.com",
        date= AMERICAN_DATE
        recommendations={'USER SKILLS EXPERIENCES HERE': ['Take from MONGODB']}
    )