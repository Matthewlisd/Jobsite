import os
import mysql.connector
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from dotenv import load_dotenv  # pip install python-dotenv
import torch
from torch.nn.functional import cosine_similarity
from transformers import AlbertTokenizer, AlbertModel
from datetime import date as DATE
from pymongo import MongoClient


#Import pretrained BERT
tokenizer = AlbertTokenizer.from_pretrained('albert-base-v2')
model = AlbertModel.from_pretrained('albert-base-v2')


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
Mongo_string = os.getenv("Mongo_string")

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
        user_data = mycursor.fetchall()
        #print(user_data)
        user_dict = {}
        for u in user_data:
            if u[0] not in user_dict.keys():
                user_dict[u[0]] = str(u[1]) + ", " + str(u[2]) + " years of experiece, " + "Confidence level: " + str(u[3]) + "."
            
            else:
                user_dict[u[0]] += str(u[1]) + ", " + str(u[2]) + " years of experiece, " + "Confidence level: " + str(u[3]) + "."
        #print(user_dict)
        user_emails = []
        user_profiles = []
        for key, value in user_dict.items():
            user_emails.append(key)
            user_profiles.append(value)


#Set up today's date for email sending
TODAY = DATE.today()
AMERICAN_DATE = TODAY.strftime("%B %d, %Y")


#GET JOB_QUALIFICATIONS from MONGODB
client = MongoClient(Mongo_string)
db = client["JobSite"]
collection = db["jobs"]
jobs = collection.find({}, {"id":1, "title":1, "qualification":1})
job_id = []
job_qualifications = []
job_titles = []
#Append job URLs here once it's avalible
job_url = []
for i in jobs:
    job_id.append(i['id'])
    job_qualifications.append(i['qualification'])
    job_titles.append(i['title'])
    #Append then URL is ready
    #job_url.append()

#Data extracted, connection closed
mycursor.close()
connection.close()
client.close()
print("Connection closed.")
# Convert descriptions to embeddings
user_embeddings = []
job_embeddings = []

for profile in user_profiles:
    encoded_input = tokenizer(profile, return_tensors='pt', padding='max_length', truncation=True, max_length=512)
    with torch.no_grad():
        output = model(**encoded_input)
        user_embeddings.append(output.last_hidden_state[0, 0, :])

for job in job_qualifications:
    encoded_input = tokenizer(job, return_tensors='pt', padding='max_length', truncation=True, max_length=512)
    with torch.no_grad():
        output = model(**encoded_input)
        job_embeddings.append(output.last_hidden_state[0, 0, :])

# Convert lists of tensors to 2D tensors for similarity computation
user_embeddings = torch.stack(user_embeddings)
job_embeddings = torch.stack(job_embeddings)

# Compute recommendations for each user
num_recommendations = min(10, len(job_qualifications))
recommendations = {}
#recommend_names = {}

for i, user_embed in enumerate(user_embeddings):
    # Using unsqueeze to get shape (1, embedding_dim) for the user_embed tensor
    similarities = [cosine_similarity(user_embed.unsqueeze(0), job_embed.unsqueeze(0)).item() for job_embed in job_embeddings]
    
    # Sort jobs by similarity
    _, indices = torch.topk(torch.tensor(similarities), num_recommendations)
    
    recommendations[user_emails[i]] = [[job_id[j] for j in indices.numpy()], [job_titles[j] for j in indices.numpy()]]

    #recommend_names[user_emails[i]] = [job_titles[j] for j in indices.numpy()]

    #Once URL data becomes avalible, append them to this dictionary
    #recoomend_urls[]
    #print(recommendations)


####

#Compile Email that sends out the recommendatations
def send_email(subject, receiver_email, name, date, R):
    # Create the base text message.
    msg = EmailMessage()
    msg["Subject"] = subject
    Title = "Your Job Recommendations"
    msg["From"] = formataddr((Title, f"{sender_email}"))
    msg["To"] = receiver_email
    msg["BCC"] = sender_email

    # Add the html version.  This converts the message into a multipart/alternative
    # container, with the original text message as the first part and the new html
    # message as the second part.
    jobs_html = '<ul>'
    for job in R[1]:
        jobs_html += f"<li>{job}</li>"
    jobs_html += '</ul>'
    msg.set_content(
        f"""\
    <html>
      <body>
        <p>Hi {name},</p>
        <p>Here is the list of jobs recommended for you today, {date}<p>
        {jobs_html}
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
    for key, value in recommendations.items():
        send_email(
            subject="Your Job Recommnedations",
            name= key,
            receiver_email="matthewlisd@gmail.com",
            date= AMERICAN_DATE,
            R= value
    )
    