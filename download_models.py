import os
import nltk
from sentence_transformers import SentenceTransformer

def download_models():
    os.makedirs('./models' , exist_ok = True)
    model = SentenceTransformer('paraphrase-MiniLM-L3-v2')
    model.save('./models/sentence_model')
    os.environ['NLTK_DATA'] = './models/nltk_data'
    nltk.download('punkt' , download_dir = './model/nltk_data')
    nltk.download('stopwords' , download_dir = './model/nltk_data')
if __name__ == "__main__":
    download_models()


