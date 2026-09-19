# MusicTrivia.github.io
Music trivia built by OpenAI API

Music Millionaire is a game ChatGPT constructed in Python that uses the OpenAI API to generate rock music trivia questions. The player answers multiple-choice questions and wins points for correct answers, and the program keeps track of the score throughout the game. The player has an option to leave the game with the points they already won or continue playing to win more points. There is also 50/50 option that lets the player pick between two options. 

This code uses the OpenAI Python library to send a request to the OpenAI API. It asks ChatGPT model to generate trivia questions and answer options. The OpenAI API returns the generated question data, and the Python program displays it under a neater user interface and the theme "Who Wants to be a Millionaire?"

The API key is lstored in `.env` file using `python-dotenv`, so the secret key is not stored in the GitHub repository.


Installed these Python packages:
python3 -m pip install openai python-dotenv pydantic


Important prompts (Codex ChatGPT  5.6 Sol):
"The project has a local .env file containing OPENAI_API_KEY. Do not read, print, expose, or modify the key. Make a simple app.py that uses my OpenAI API key from .env to ask for one easy rock music trivia question and print the response."

"So now edit app.py so it makes a 5 question rock music trivia quiz. Each question should have four choices, the user would type A B C or D and the program has to keep score and show the final score."

"Can you give this a simple user interface"

"Let's turn this to who wants to be a millionaire game"

"The game should also store your highest cash prize."

"I want the color scheme to match the original show. You can make up a simple similar logo but adjacent to it so we didnt  "steal" the logo"

"Now there are some issues with dimensioning. The 50:50 text is cut on the bottom and if i minimize the window it does show the buttons. Make it so that things would fit and resize accordingly"