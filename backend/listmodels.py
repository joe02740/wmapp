import anthropic

client = anthropic.Anthropic()

models = client.models.list(limit=20)
print(models)