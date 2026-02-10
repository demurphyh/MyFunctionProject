# Database Choice

## Chosen Database

Azure Cosmos DB

## Justification

I believe that CosmosDB is the best fit in this case for easily handling the JSON data received from the TextAnalyzer function without needing to setup a schema. Using the serverless throughput option or the free plan allows it be a cost effective solution as it will only charge for the requests made. Also, it is easy to query data using the partition key to easily search through the historical data using the GetAnalysisHistory API.

## Alternatives Considered

- Azure Table Storage: Azure Table Storage was the closest contender in my analysis but I decided not to go with it as it does not index as well as CosmosDB, it's slightly slower than CosmosDB and it doesn't scale as well as CosmosDB.

- Azure SQL: I chose not to go with Azure SQL because setting up a relational schema in order to track JSON data seemed inefficient for the task and woulkd be much more complex than CosmosDB.

- Azure Blob Storage: I did not choose this options because it seems like it would be harder to search and filter results when trying to retreive historical data.

## Cost Consideration

The biggest considration with using CosmosDB is the free tier that it provides which allows 1000 request units per second and 25 GBs per month for free which will be more than enough for this lab. If we were to surpass that amount CosmosDB is still very cheap when used in serverless mode especiallya the the low requirements of this lab.
