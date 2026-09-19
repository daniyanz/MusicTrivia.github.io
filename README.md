# MusicTrivia.github.io
Music trivia built by OpenAI API

Music Millionaire is a game ChatGPT constructed in Python that uses the OpenAI API to generate rock music trivia questions. The player answers multiple-choice questions and wins points for correct answers, and the program keeps track of the score throughout the game. The player has an option to leave the game with the points they already won or continue playing to win more points. There is also 50/50 option that lets the player pick between two options. 

This code uses the OpenAI Python library to send a request to the OpenAI API. It asks ChatGPT model to generate trivia questions and answer options. The OpenAI API returns the generated question data, and the Python program displays it under a neater user interface and the theme "Who Wants to be a Millionaire?"

The API key is lstored in `.env` file using `python-dotenv`, so the secret key is not stored in the GitHub repository.


Installed these Python packages:
python3 -m pip install openai python-dotenv pydantic