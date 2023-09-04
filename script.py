import mysql.connector
from bs4 import BeautifulSoup
import re
import os
from dotenv import load_dotenv
from pathlib import Path
from pymongo import MongoClient

try:
    # Replace these values with your actual Bluehost database credentials
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

    # Establish the connections
    connection = mysql.connector.connect(
        host=db_host,
        user=db_user,
        password=db_password,
        database=db_database
    )

    client = MongoClient(Mongo_string)
    db = client["JobSite"]
    collection = db["jobs"]

    
    if connection.is_connected():
        mycursor = connection.cursor()
        #print("Connected to the database.")
        """
        #Find User id, Details from users
        mycursor.execute("SELECT id, email, Details FROM smartend_users")

        CV_Details = mycursor.fetchall()

        #Find unique user id, skills, years and level from database
        mycursor.execute("SELECT Id, UserId, Skill, Years, Level FROM smartend_mbamade_skills")
        Skills = mycursor.fetchall()
        
        for m in CV_Details:
            print(m)
        for s in Skills:
            print(s)
        """
        #print(Skills[0][0])

        #Anyway to combine those two datas?
        """
            Store All the data in a databse? or take out when needed? Take out when needed
        """
        #JOB DATA
        mycursor.execute("SELECT title_en, JobCompany, details_en, id FROM smartend_topics WHERE webmaster_id = 19 and status = 1")
        Jobs = mycursor.fetchall()

        Ids = [row[3] for row in Jobs]
        #Clean DATA, espeacially details_en, put in MONGO
        for i in Jobs:
            #Test if it's already in Database
            existing_document = collection.find_one({"id": i[3]})
            if not existing_document:
            ###########
                gfg = BeautifulSoup(i[2], features="lxml")
                res = gfg.get_text().lower().strip()
                keyword = "qualification"
                endword = "hiring insights"
                index = res.find(keyword)  # Find the index of the keyword (case-insensitive)
                enddex = res.find(endword)
                if index != -1:
                    extracted_text = re.sub(r'\n+', '\n', res[index + len(keyword):enddex])   #.replace("\n\n", "\n")
                    if extracted_text[0] == 's':
                        extracted_text = extracted_text[1:].strip()
                    print(extracted_text)
                    job_data = { "id":i[3], 'title':i[0] , 'company':i[1], 'qualification': extracted_text}
                    collection.insert_one(job_data)
        print(Ids)
        #print(i)

        #Remove unwanted data that's no longer open
        delete_result = collection.delete_many({"id": {"$nin": Ids}})
        print(f"Deleted {delete_result.deleted_count} documents.")

        # Close the cursor and connection when done
        mycursor.close()
        connection.close()
        print("Connection closed.")

except mysql.connector.Error as error:
    print("Error connecting to Bluehost database:", error)