using System.Text.Json.Serialization;
using MediaBrowser.Model.Plugins;

namespace Jellyfin.Plugin.Agent;

/// <summary>
/// 插件配置，持久化到服务器端（XML），由配置页保存。
/// </summary>
public class AgentConfig : BasePluginConfiguration
{
    [JsonPropertyName("deepSeekApiKey")]
    public string DeepSeekApiKey { get; set; } = string.Empty;

    [JsonPropertyName("deepSeekBaseUrl")]
    public string DeepSeekBaseUrl { get; set; } = "https://api.deepseek.com";

    [JsonPropertyName("deepSeekModel")]
    public string DeepSeekModel { get; set; } = "deepseek-chat";

    [JsonPropertyName("sidecarUrl")]
    public string SidecarUrl { get; set; } = "http://127.0.0.1:8787";

    // 留空则由插件按当前请求自动推导。
    [JsonPropertyName("jellyfinUrl")]
    public string JellyfinUrl { get; set; } = string.Empty;

    // 给 Agent 控制媒体用（Dashboard → API Keys 生成）。
    [JsonPropertyName("jellyfinApiKey")]
    public string JellyfinApiKey { get; set; } = string.Empty;
}
