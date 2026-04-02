import asyncio

from src.infrastructure.context import AppContext
from src.agents.vision import describe_image
from src.agents.text import summarize
from src.telegram.save_msgs import raw_msgs_to_db


async def main():

    await raw_msgs_to_db()

    # async with AppContext(verbose=True) as ctx:
    #     await ctx.use_model("vision")
    #     description = await describe_image(ctx.llm, "/Users/stepan/Documents/Dev/familybot/daimond.png")

    #     await ctx.use_model("gigachat")
    #     summary = await summarize(ctx.llm, description)
    #     print(summary)


if __name__ == '__main__':
    asyncio.run(main())