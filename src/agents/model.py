# from src.infrastructure.context import AppContext


# async def get_model():
#     async with AppContext(verbose=False) as ctx:
#         await ctx.use_model("vision")
#         description = await describe_image(ctx.llm, "/Users/stepan/Documents/Dev/familybot/daimond.png")

#         await ctx.use_model("gigachat")
#         summary = await summarize(ctx.llm, description)
