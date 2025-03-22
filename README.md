# chainlit_bot
AI Powered Bot that books calendar meetings for you.
To run the chat bot, enter 'chainlit run app.py' in the project's root directory.
The bot can create new meetings, list all your bookings, cancel meetings and reschedule meetings. 
The bot uses OpenAI's function calling feature which allows GPT models to use the functions defined in the cal.com api to make API calls on behalf of the app 
depending on user prompts.

The workflow:
1. User enters prompt into the chatbot interface
2. OpenAI client is initialised through the OpenAI API to receive prompts and process the inputs
3. The app calls upon the openai_function_calling function which takes in the user session, user id and prompt.
4. The correct user session is obtained with the user's user_id which is user by default - where the user sessions contains details about the conversation history, pending functions and pending parameters.
5. We add the prompt to the session's conversation history under the role of user to give Gpt 4o the latest context.
6. If there are pending functions based on the tools the Gpt 4o model wanted to use but didn't have all the parameters for, the Gpt model is instructed to extract missing parameters for those functions so the corresponding pending functions can be executed.
7. If there are no pending functions, the Gpt 4o model is instructed to be a helpful assistant that helps the user book and manage events.
8. The Gpt 4o model uses the session's conversation history consisting of the latest user prompt to decide the corresponding functions and parameters to call based on the functions schema provided to OpenAI.
9. If there are missing fields for the chosen function call, the Gpt 4o model immediately asks the user to provide the missing arguments as well while initialising the pending function and pending arguments to what it extracted.
10. The open_ai_functions program then finally calls the handle_function_call function which actually calls the calcom api functions
11. The function results/responses from the calcom api functions is sent back to the Gpt 4o model by being appended to the conversation history to provide context to the Gpt 4o model
12. The Gpt 4o model then generates a response accordingly to tell the user about the status of their booking changes based on the api call results
13. If there are no tool calls, the Gpt 4o response based on the first prompt is returned back to the user.
 
