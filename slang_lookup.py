import pandas as pd
import os
from llama_client import summarize_definition

class SlangDictionary:
    def __init__(self, data_dir='urbandict'):
        #csv_path = os.path.join(data_dir, 'checkpoint2_dataset.csv')
        #csv_path = os.path.join(data_dir, 'slangbridge_training_data.csv')
        csv_path = os.path.join(data_dir, 'slangbridge_complete_dataset.csv')

        self.df = pd.read_csv(csv_path)
        self.df['slang_term'] = self.df['slang_term'].str.lower()

    def lookup(self, term):
        term_lower = term.lower().strip()
        row = self.df[self.df['slang_term'] == term_lower]

        if not row.empty:
            definition = row.iloc[0]['standard_translation']
            summary = summarize_definition(term, definition)
            return f"{definition}\n\n✏️ Simple Summary: {summary}"

        return None
