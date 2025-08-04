from slang_lookup import SlangDictionary
from llama_client import query_llama
from web_scraper import scrape_urban_dictionary

FALLBACK_RESPONSE = "Sorry, seems like I'm still learning more and more everyday! Check back soon and I'll have an answer to your question."

def main():
    slang_dict = SlangDictionary()

    print("Welcome to the SlangBridge Chatbot! (Type 'exit' to quit)\n")

    while True:
        user_input = input("What slang term can I translate for you?: ").strip()
        if user_input.lower() == 'exit':
            print("Goodbye!")
            break

        # 1. Try local lookup
        result = slang_dict.lookup(user_input)
        if result:
            print("🟢 According to the Data:", result)
            continue

        # 2. Try LLAMA API
        print("🔍 I can't get a proper response from the data we have. Asking LLAMA to scrape urban dictionary...")
        llama_result = query_llama(user_input)
        if llama_result:
            print("🤖 LLAMA says:", llama_result)
            continue

        # 3. Try scraping Urban Dictionary
        print("🌐 Asking Urban Dictionary online...")
        scraped_result = scrape_urban_dictionary(user_input)
        if scraped_result:
            print(f"\n📘 Meaning:\n{scraped_result}")
        else:
            print("⚠️", FALLBACK_RESPONSE)

if __name__ == "__main__":
    main()