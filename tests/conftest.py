import os

# Set contacts DB to in-memory to prevent interference from persistent database
os.environ["AND9_CONTACTS_DB"] = ":memory:"
