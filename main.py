import asyncio
import pprint

from src.msg_processor.collect_msg import save_msgs


async def main():

    result = await save_msgs()
    print(result)
    # pprint.pprint(get_result)
    # async with AppContext(verbose=True) as ctx:
    #     await ctx.use_model("vision")
    #     description = await describe_image(ctx.llm, "/Users/stepan/Documents/Dev/familybot/daimond.png")

    #     await ctx.use_model("gigachat")
    #     summary = await summarize(ctx.llm, description)
    #     print(summary)


if __name__ == '__main__':
    asyncio.run(main())