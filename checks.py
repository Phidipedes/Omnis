def messageCheck(ctx):

    """
    Message check for user input

    Checks that the message comes from the same user in the same channel.

    Parameters:
        ctx (Context): The command invocation context.

    """

    def check(message):

        return message.author == ctx.author and message.channel == ctx.channel

    return check