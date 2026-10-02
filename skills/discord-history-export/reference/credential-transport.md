# Credential transport evidence

The helper supplies the authorized bot credential through the exporter child environment as `DISCORD_TOKEN`. It never constructs a token argument. DCE infers token type; a deprecated bot flag is unnecessary.

The source for [DiscordChatExporter release 2.47](https://github.com/Tyrrrz/DiscordChatExporter/blob/2.47/DiscordChatExporter.Cli/Commands/Base/DiscordCommandBase.cs) binds its token option using `EnvironmentVariable = "DISCORD_TOKEN"`. Release help may omit environment-variable names. The helper accepts release 2.47 based on that source binding, while still checking the actual executable's reported version and selected export command's help.

An independent current-source reference is [revision 427c6021ac2dca4a76fbcbe553130f992a3305e1](https://github.com/Tyrrrz/DiscordChatExporter/blob/427c6021ac2dca4a76fbcbe553130f992a3305e1/DiscordChatExporter.Cli/Commands/Base/DiscordCommandBase.cs), whose source-file SHA-256 is `2cec72197132a749701cb83e39a1a5c79ac08bcbf750f33cbd3648ef49228fc7`. It confirms the environment binding and token-type inference. Current-source evidence alone does not establish an installed release's behavior.

For other releases, the local export-command help must explicitly identify `DISCORD_TOKEN`, or preflight refuses execution. New source-proven releases need a reviewed evidence update. There is no token-argument fallback.

The offline fixtures simulate a supported release whose help deliberately omits the environment variable, plus an unknown release with no transport proof. That proves the helper's decision path; it does not certify a downloaded executable or a real Discord session.
