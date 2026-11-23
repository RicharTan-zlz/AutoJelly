using System.Collections.Generic;
using MediaBrowser.Common.Configuration;
using MediaBrowser.Common.Plugins;
using MediaBrowser.Model.Plugins;
using MediaBrowser.Model.Serialization;

namespace Jellyfin.Plugin.Agent;

public class AgentPlugin : BasePlugin<AgentConfig>, IHasWebPages
{
    public AgentPlugin(IApplicationPaths applicationPaths, IXmlSerializer xmlSerializer)
        : base(applicationPaths, xmlSerializer)
    {
    }

    public override string Name => "Jellyfin Agent";

    public override string Description => "AI assistant (DeepSeek) embedded in the Jellyfin web UI";

    public IEnumerable<PluginPageInfo> GetPages()
    {
        return new[]
        {
            new PluginPageInfo
            {
                Name = "JellyfinAgentPage",
                DisplayName = "AI 助手",
                // 嵌入资源 manifest 名 = RootNamespace + "." + 文件名。
                EmbeddedResourcePath = "Jellyfin.Plugin.Agent.chat.html",
                EnableInMainMenu = true,
                MenuSection = "server",
                MenuIcon = "smart_toy"
            }
        };
    }
}
