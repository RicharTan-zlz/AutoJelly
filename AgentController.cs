using System.Net.Http.Json;
using System.Text.Json.Serialization;
using MediaBrowser.Common.Api;
using MediaBrowser.Common.Plugins;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Jellyfin.Plugin.Agent;

[ApiController]
[Route("JellyfinAgent")]
public class AgentController : ControllerBase
{
    private readonly IPluginManager _pluginManager;

    public AgentController(IPluginManager pluginManager)
    {
        _pluginManager = pluginManager;
    }

    private AgentPlugin GetPlugin()
    {
        var plugin = _pluginManager.Plugins
            .FirstOrDefault(p => p.Instance is AgentPlugin)
            ?.Instance as AgentPlugin;

        return plugin ?? throw new InvalidOperationException("Jellyfin Agent plugin is not loaded.");
    }

    [HttpGet("health")]
    [Authorize]
    public ActionResult Health() => Ok(new { ok = true, now = DateTime.UtcNow });

    [HttpGet("config")]
    [Authorize(Policy = Policies.RequiresElevation)]
    public ActionResult<AgentConfig> GetConfig() => Ok(GetPlugin().Configuration);

    [HttpPost("config")]
    [Authorize(Policy = Policies.RequiresElevation)]
    public ActionResult SaveConfig([FromBody] AgentConfig config)
    {
        GetPlugin().UpdateConfiguration(config);
        return Ok(new { ok = true });
    }

    [HttpPost("chat")]
    [Authorize]
    public async Task<ActionResult> Chat([FromBody] ChatRequest request)
    {
        var config = GetPlugin().Configuration;

        var jellyfinUrl = string.IsNullOrWhiteSpace(config.JellyfinUrl)
            ? $"{Request.Scheme}://{Request.Host}"
            : config.JellyfinUrl;

        var payload = new
        {
            message = request.Message,
            history = request.History,
            deepseek_api_key = config.DeepSeekApiKey,
            deepseek_base_url = config.DeepSeekBaseUrl,
            deepseek_model = config.DeepSeekModel,
            jellyfin_url = jellyfinUrl,
            jellyfin_api_key = config.JellyfinApiKey
        };

        try
        {
            using var client = new HttpClient { Timeout = TimeSpan.FromMinutes(2) };
            var response = await client.PostAsJsonAsync($"{config.SidecarUrl.TrimEnd('/')}/chat", payload);
            var body = await response.Content.ReadAsStringAsync();

            return response.IsSuccessStatusCode
                ? Content(body, "application/json")
                : StatusCode((int)response.StatusCode, body);
        }
        catch (Exception)
        {
            return Ok(new { reply = "无法连接 AI 服务，请确认「启动 AI 助手」的窗口还开着。" });
        }
    }
}

public sealed class ChatRequest
{
    [JsonPropertyName("message")]
    public string Message { get; set; } = string.Empty;

    [JsonPropertyName("history")]
    public List<ChatMessage> History { get; set; } = new();
}

public sealed class ChatMessage
{
    [JsonPropertyName("role")]
    public string Role { get; set; } = string.Empty;

    [JsonPropertyName("content")]
    public string Content { get; set; } = string.Empty;
}
