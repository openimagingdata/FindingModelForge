# Musings

## Databases

- Could we use in-process [LanceDB](https://lancedb.github.io/lancedb/) or [txtai](https://neuml.github.io/txtai/) as our semantic searchable store? They seems to have a lot of good built-in database capabilities that we could leverage. This could be terrific for the containers that are managing report text—we can put a little front-end on them such that you can upload a bunch of report texts, and then everything just sits inside the container.
- Thought about the below—I think the answer has to be, "No, we should double down on using MongoDB as hard as we can, especially pushing the Beanie ODM.
_Could we use SQLite more—even as the production back-end for our system? There's a tool called Litestream that essentially does live replication of the database changes to a storage where it can be replayed anywhere for replication. (This can be part of the deployment process, even, I think.)_

## Front-end

- I'm thinking we can use [NiceGUI](https://nicegui.io) to build up the front-end rather than Streamlit.
- We can run both the front-end and any API endpoints we want to create on the same FastAPI instance.
- We can use the Github OAuth examples built with it, which seem to maintain the authorization in the session.

## Back-end

- Beanie has associated with it a queue system: [Queue](https://beanie-odm.dev/batteries/queue/), which should be great for what we need. We can use it offload processing from the FastAPI system.

## Deployment

- It should be possible to deploy using Azure command line tools directly from the local repository for our web app.
- We should be able to automate deployment of the library to the PyPI repository (if they ever approve our organization application)
