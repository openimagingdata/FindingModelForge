# Musings

## Databases

- Could we use in-process [LanceDB](https://lancedb.github.io/lancedb/) as our vector database, and general database for things that require semantic search capabilities? It seems to have a lot of good built-in database capabilities that we could leverage. This could be terrific for the containers that are managing report text—we can put a little front-end on them such that you can upload a bunch of report texts, and then everything just sits inside the container.
- Thought about the below—I think the answer has to be, "No, we should double down on using MongoDB as hard as we can, especially pushing the Beanie ODM.  
_Could we use SQLite more—even as the production back-end for our system? There's a tool called Litestream that essentially does live replication of the database changes to a storage where it can be replayed anywhere for replication. (This can be part of the deployment process, even, I think.)_

## Front-end

- I'm thinking we can use FastHTML to build up the front-end rather than Streamlit, but I'd like to see how to manage a more complex app using it. But it looks like it could be very good.
  - It looks like it has straightforward Github OAuth built into it, which would be a big step forward. Should be able to pass the token right along to FastAPI as needed; will figure this out.

## Back-end

- Beanie has associated with it a queue system: [Queue](https://beanie-odm.dev/batteries/queue/), which should be great for what we need. We can use it offload processing from the FastAPI system.  
_I read a really good article about a library for back-end job processing called "Redis Queue" (that uses Redis as a backplane, obviously)._

## Deployment

- It should be possible to deploy using Azure command line tools directly from the local repository for both our front end and back end.
- For the local containers, we can use the Supervisor tool to run both the front and back end in the same container for simplicity.
