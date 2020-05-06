"""
Cog for executing source code from Discord channel chat message.
"""

import re
import json
import base64
import aiohttp
from http.client import responses
from datetime import datetime

import discord
from discord.ext import commands
from discord import Embed, Color


from typing import Optional
from bot.constants import Lang, NEWLINES_LIMIT, CHARACTERS_LIMIT, Emoji, PREFIX


class Execution(commands.Cog):
    """
    Represents a Cog for executing source codes.
    """

    def __init__(self, bot):
        self.bot = bot

    async def __create_output_embed(
        self,
        token: str,
        source_code: Optional[str],
        stdout: str,
        stderr: str,
        compile_output: str,
        time: float,
        memory: int,
        language: str,
        language_id: int,
        language_icon: str,
        description: str,
        author_name: str,
        author_icon: str,
    ):
        """
        Creates a Discord embed for the submission execution.
        
        Includes:
            Author of the submission.
            Green or red color of the embed depending on the description.
            Output (stdout, stderr, compile output)
            Link for full output (if any)
            Time and memeroy usage
            Language name, icon and version.
            Datetime of the execution.
        """
        ide_link = "https://ide.judge0.com/?"
        color = Color.green() if description == "Accepted" else Color.red()

        embed = Embed(colour=color, timestamp=datetime.utcnow())
        embed.set_author(name=f"{author_name}'s code execution", icon_url=author_icon)

        output = str()
        if stdout:
            output += base64.b64decode(stdout.encode()).decode()
        if stderr:
            output += base64.b64decode(stderr.encode()).decode()
        if compile_output and not output:
            output += base64.b64decode(compile_output.encode()).decode()
        if not output:
            output = "No output"

        print(len(output))
        print(output.count("\n"))

        if len(output) > 300 or output.count("\n") > 10:
            embed.description = f"Output too large - [Full output]({ide_link}{token})"

            if output.count("\n") > 10:
                output = "\n".join(output.split("\n")[:10]) + "\n(...)"
            else:
                output = output[:300] + "\n(...)"
        else:
            embed.description = f"Edit this code in an online IDE - [here]({ide_link}{token})"

        embed.add_field(name="Output", value=f"```yaml\n{output}```", inline=False)

        if time:
            embed.add_field(name="Time", value=f"{time} s")
        if memory:
            embed.add_field(name="Memory", value=f"{round(memory / 1000, 2)} MB")
        embed.set_footer(text=f"{language} | {description}", icon_url=language_icon)

        return embed

    def __create_how_to_pass_embed(self, lang):
        """
        Creates a Discord embed guide for passing code.

        Includes the 3 methods of passing source code.
        """
        embed = Embed(title=f"How to pass {lang.version.split('(')[0]}source code?")

        embed.set_thumbnail(url=lang.icon)
        embed.add_field(
            name="Method 1 (Plain)",
            value=(f"{PREFIX}{lang.command}\n" "code"),
            inline=False,
        )
        embed.add_field(
            name="Method 2 (Code block)",
            value=(f"{PREFIX}{lang.command}\n" "\`\`\`code\`\`\`"),
            inline=False,
        )
        embed.add_field(
            name="Method 3 (Syntax Highlighting)",
            value=(f"{PREFIX}{lang.command}\n" f"\`\`\`{lang.command}\n" "code\`\`\`"),
            inline=False,
        )
        return embed

    async def __execute_code(self, ctx, lang, code: Optional[str]):
        """
        The main method for executing source code from a message.

        If version check is passed for arg - it sends language version only.

        The steps for executing code:
            strips the source code
            creates and waits for sumbission output

            if is error it sends the error
            otherwise it creates an embed for the output and sends it in the same chat
        """
        print(lang)
        print(code)

        if code == None:
            await ctx.send(embed=self.__create_how_to_pass_embed(lang))
            await ctx.message.add_reaction(Emoji.Execution.idle)
            return

        if code.startswith("-v") or code.startswith("-version"):
            await ctx.send(f"> {lang.version}")
            await ctx.message.add_reaction(Emoji.Execution.idle)
            return

        await ctx.message.add_reaction(Emoji.Execution.loading)
        code = self.strip_source_code(code)
        submission = await self.get_submission(code, lang)

        if isinstance(submission, str):  # it is error code
            await ctx.message.add_reaction(Emoji.Execution.offline)
            await ctx.send(submission)
            await ctx.message.remove_reaction(
                Emoji.Execution.loading, self.bot.user
            )
            return

        await ctx.send(
            embed=await self.__create_output_embed(
                token=submission["token"],
                source_code=submission["source_code"],
                stdout=submission["stdout"],
                stderr=submission["stderr"],
                compile_output=submission["compile_output"],
                time=submission["time"],
                memory=submission["memory"],
                language=lang.version,
                language_id=submission["language_id"],
                language_icon=lang.icon,
                description=submission["status"]["description"],
                author_name=str(ctx.message.author),
                author_icon=ctx.message.author.avatar_url,
            )
        )
        if submission["status"]["description"] == "Accepted":
            await ctx.message.add_reaction(Emoji.Execution.successful)
        else:
            await ctx.message.add_reaction(Emoji.Execution.error)
        await ctx.message.remove_reaction(
            Emoji.Execution.loading, self.bot.user
        )

    @commands.group(pass_context=True, aliases=list(Lang.ids.keys()))
    async def run(self, ctx, *, code: Optional[str]):
        await self.__execute_code(ctx, Lang.ids[str(ctx.invoked_with)], code)
        # if ctx.invoked_subcommand is None:
        #     await ctx.wait('Invalid sub command passed...')

    # @run.command(name=Lang.Assembly.command)
    # async def execute_assembly(self, ctx, *, code: Optional[str]):
    #     """Executes Assembly code."""
    #     await self.__execute_code(ctx, Lang.Assembly, code)

    # @run.command(name=Lang.Bash.command, aliases=Lang.Bash.aliases)
    # async def execute_bash(self, ctx, *, code: Optional[str]):
    #     """Executes Bash code."""
    #     await self.__execute_code(ctx, Lang.Bash, code)

    # @run.command(name=Lang.C.command)
    # async def execute_c(self, ctx, *, code: Optional[str]):
    #     """Executes C code."""
    #     await self.__execute_code(ctx, Lang.C, code)

    # @run.command(name=Lang.Cpp.command, aliases=Lang.Cpp.aliases)
    # async def execute_cpp(self, ctx, *, code: Optional[str]):
    #     """Executes C++ code."""
    #     await self.__execute_code(ctx, Lang.Cpp, code)

    # @run.command(name=Lang.CSharp.command, aliases=Lang.CSharp.aliases)
    # async def execute_csharp(self, ctx, *, code: Optional[str]):
    #     """Executes C# code."""
    #     await self.__execute_code(ctx, Lang.CSharp, code)

    # @run.command(name=Lang.CommonLisp.command)
    # async def execute_lisp(self, ctx, *, code: Optional[str]):
    #     """Executes Common Lisp code."""
    #     await self.__execute_code(ctx, Lang.CommonLisp, code)

    # @run.command(name=Lang.D.command)
    # async def execute_d(self, ctx, *, code: Optional[str]):
    #     """Executes D code."""
    #     await self.__execute_code(ctx, Lang.D, code)

    # @run.command(name=Lang.Elixir.command)
    # async def execute_elixir(self, ctx, *, code: Optional[str]):
    #     """Executes Elixir code."""
    #     await self.__execute_code(ctx, Lang.Elixir, code)

    # @run.command(name=Lang.Erlang.command)
    # async def execute_erlang(self, ctx, *, code: Optional[str]):
    #     """Executes Erlang code."""
    #     await self.__execute_code(ctx, Lang.Erlang, code)

    # @run.command(name=Lang.Go.command, aliases=Lang.Go.aliases)
    # async def execute_go(self, ctx, *, code: Optional[str]):
    #     """Executes Golang code."""
    #     await self.__execute_code(ctx, Lang.Go, code)

    # @commands.command(name=Lang.Haskell.command)
    # async def execute_haskell(self, ctx, *, code: Optional[str]):
    #     """Executes Haskell code."""
    #     await self.__execute_code(ctx, Lang.Haskell, code)

    # @commands.command(name=Lang.Java.command)
    # async def execute_java(self, ctx, *, code: Optional[str]):
    #     """Executes Java code."""
    #     await self.__execute_code(ctx, Lang.Java, code)

    # @commands.command(name=Lang.JavaScript.command, aliases=Lang.JavaScript.aliases)
    # async def execute_js(self, ctx, *, code: Optional[str]):
    #     """Executes JavaScript code."""
    #     await self.__execute_code(ctx, Lang.JavaScript, code)

    # @commands.command(name=Lang.Lua.command)
    # async def execute_lua(self, ctx, *, code: Optional[str]):
    #     """Executes Lua code."""
    #     await self.__execute_code(ctx, Lang.Lua, code)

    # @commands.command(name=Lang.OCaml.command)
    # async def execute_ocaml(self, ctx, *, code: Optional[str]):
    #     """Executes OCaml code."""
    #     await self.__execute_code(ctx, Lang.OCaml, code)

    # @commands.command(name=Lang.Octave.command)
    # async def execute_octave(self, ctx, *, code: Optional[str]):
    #     """Executes Octave code."""
    #     await self.__execute_code(ctx, Lang.Octave, code)

    # @commands.command(name=Lang.Pascal.command)
    # async def execute_pascal(self, ctx, *, code: Optional[str]):
    #     """Executes Pascal code."""
    #     await self.__execute_code(ctx, Lang.Pascal, code)

    # @commands.command(name=Lang.Php.command)
    # async def execute_php(self, ctx, *, code: Optional[str]):
    #     """Executes PHP code."""
    #     await self.__execute_code(ctx, Lang.Php, code)

    # @commands.command(name=Lang.Prolog.command)
    # async def execute_prolog(self, ctx, *, code: Optional[str]):
    #     """Executes Prolog code."""
    #     await self.__execute_code(ctx, Lang.Prolog, code)

    # @run.command(name=Lang.Python.command, aliases=Lang.Python.aliases)
    # async def execute_python(self, ctx, *, code: Optional[str]):
    #     """Executes Python code."""
    #     await self.__execute_code(ctx, Lang.Python, code)

    # @commands.command(name=Lang.Ruby.command)
    # async def execute_ruby(self, ctx, *, code: Optional[str]):
    #     """Executes Ruby code."""
    #     await self.__execute_code(ctx, Lang.Ruby, code)

    # @commands.command(name=Lang.Rust.command)
    # async def execute_rust(self, ctx, *, code: Optional[str]):
    #     """Executes Rust code."""
    #     await self.__execute_code(ctx, Lang.Rust, code)

    # @commands.command(name=Lang.TypeScript.command)
    # async def execute_typescript(self, ctx, *, code: Optional[str]):
    #     """Executes TypeScript code."""
    #     await self.__execute_code(ctx, Lang.TypeScript, code)

    @staticmethod
    def prepare_paylad(source_code: Optional[str],
                             language_id: int,
                             stdin: str = ""):
        base64_code = base64.b64encode(source_code.encode()).decode()
        base64_stdin= base64.b64encode(stdin.encode()).decode()
        payload = {"source_code": base64_code, "language_id": language_id, "stdin": base64_stdin}

        return payload

    @staticmethod
    async def get_submission(
        source_code: Optional[str], language_id: int, stdin=""
    ) -> dict:
        """
        Sends submission in judge0 API and waits for output.
        """
        base_url = "https://api.judge0.com/submissions/"
        payload = Execution.prepare_paylad(source_code, language_id, stdin)
        
        async with aiohttp.ClientSession() as cs:
            async with cs.post(f"{base_url}?base64_encoded=true", json=payload) as r:
                if r.status not in [200, 201]:
                    return f"{r.status} {responses[r.status]}"
                res = await r.json()
            token = res["token"]

            print(token)

            while True:
                submission = await cs.get(f"{base_url}{token}?base64_encoded=true")
                if submission.status not in [200, 201]:
                    return f"{submission.status} {responses[submission.status]}"

                adict = await submission.json()
                if adict["status"]["id"] not in [1, 2]:
                    break
        adict["token"] = token
        adict.update(payload)
        return adict

    # @staticmethod
    # async 

    @staticmethod
    def strip_source_code(code: Optional[str]) -> str:
        """
        Strips the source code from a Discord message.
        
        It strips:
            code wrapped in backticks ` (one line code)
            code wrapped in triple backtick ``` (multiline code)
            code wrapped in triple backticks and
                 language keyword ```python (syntax highlighting)
        """
        code = code.strip("`")
        if re.match(r"\w*\n", code):
            code = "\n".join(code.split("\n")[1:])
        return code

def setup(bot):
    bot.add_cog(Execution(bot))
