A2A - MCP Hackathon 
Arch AI Data

The project is a Chatbot that help architects to get building right analysis without spending time and effort, using A2A protocol and MCP.
The code is running with Python - MCP server and client for using the server, and api for frontend ChatBot to call the mcp server.
The ChatBot is written in Angular.
After user write the address, it calls the api (now it is working without the front), and A2A protocol is starting:
1. First agent work - getting the address and translate it to geo location.
2. First agent pass the location to the Second Agent that finds the Relevant document construction plans.
3. Third Agent takes the documents and extract relevant data from it.
4. Fourth Agent responsible to create and design the PPT
MCP:
In our project, the MCP starting to work when we pull data from external services, like PDFWrite and API Maps.
We are pulling documents from external services like Mavat web site, this service is getting requests and returning the relevant document to the next Agent.

- The project Paython is at the root - Mcp server, agents and api
- The Frontend Angular is at the directory: app-web --> arch-ai-chatbot
- Also there is ppt for this project - מצגת להאקטון
- Target document that the architact is creating - זכויות בניה בניין חדש
  
