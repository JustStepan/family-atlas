import asyncio

from src.msg_assembler.assembler import prepare_msgs
from src.msg_processor.collect_msg import save_msgs


async def main():

    result = await save_msgs()
    await asyncio.sleep(2)
    print(result)

if __name__ == '__main__':

    messages_collected = asyncio.run(main())
    # print(messages_collected)
    # if messages_collected:
    print(asyncio.run(prepare_msgs()))




    # pprint.pprint(get_result)
    # async with AppContext(verbose=True) as ctx:
    #     await ctx.use_model("vision")
    #     description = await describe_image(ctx.llm, "/Users/stepan/Documents/Dev/familybot/daimond.png")

    #     await ctx.use_model("gigachat")
    #     summary = await summarize(ctx.llm, description)
    #     print(summary)