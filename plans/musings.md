# Musings

## Databases

- Could we use in-process LanceDB as our vector database, and general database for things that require semantic search capabilities? It seems to have a lot of good built-in database capabilities that we could leverage. This could be terrific for the containers that are managing report text—we can put a little front-end on them such that you can upload a bunch of report texts, and then everything just sits inside the container.
- Could we use SQLite more—even as the production back-end for our system? There's a tool called Litestream that essentially does live replication of the database changes to a storage where it can be replayed anywhere for replication. (This can be part of the deployment process, even, I think.)

## Front-end

- I'm thinking we can use FastHTML to build up the front-end rather than Streamlit, but I'd like to see how to manage a more complex app using it. But it looks like it could be very good.

## Back-end

- I read a really good article about a library for back-end job processing called "Redis Queue" (that uses Redis as a backplane, obviously).

## Deployment

- It should be possible to deploy using Azure command line tools directly from the local repository for both our front end and back end.
- For the local containers, we can use the Supervisor tool to run both the front and back end in the same container for simplicity.