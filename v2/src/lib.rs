pub mod domain;
mod store;
use domain::Record;
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    sync::{Arc, Mutex},
};
use tezbar_extension_sdk::{BoxFuture, CoreResult, Extension, ExtensionContext};
const COMMANDS: &[&str] = &["random-compliment", "quick-compliment", "gratitude-note"];
#[derive(Clone, Copy, PartialEq, Eq)]
enum Phase {
    Copy,
    Close,
    Done,
}
#[derive(Clone)]
struct Pending {
    text: String,
    phase: Phase,
}
struct Live {
    command: String,
    rows: Vec<Record>,
    tone: String,
    selected: Option<String>,
    effective_selected: Option<String>,
    search: String,
    revision: u64,
    loaded: bool,
    pending_tone: Option<String>,
    error: Option<String>,
    pending: Option<Pending>,
}
impl Live {
    fn bump(&mut self) -> Result<(), String> {
        self.revision = self
            .revision
            .checked_add(1)
            .ok_or("Session revision exhausted")?;
        Ok(())
    }
    fn pool(&self) -> Vec<Record> {
        if self.command == "gratitude-note" {
            self.rows.clone()
        } else {
            domain::pool(&self.rows, &self.tone)
        }
    }
    fn visible(&self) -> Vec<Record> {
        domain::search(&self.pool(), &self.search)
    }
    fn effective(&mut self, sample: &dyn Fn() -> Result<f64, String>) -> Result<(), String> {
        let pool = self.pool();
        if !pool.iter().any(|r| Some(&r.id) == self.selected.as_ref()) {
            self.effective_selected = domain::pick(&pool, None, sample()?)?;
        } else {
            self.effective_selected = self.selected.clone();
        }
        Ok(())
    }
    fn action(&self, verb: &str, id: &str) -> String {
        format!("{}:{verb}:{id}", self.revision)
    }
    fn view(&self) -> Value {
        if let Some(pending) = &self.pending {
            if pending.phase == Phase::Done {
                return tezbar_extension_sdk::no_view(&format!("Copied: {}", pending.text));
            }
        }
        let title = match self.command.as_str() {
            "gratitude-note" => "Gratitude Note",
            "quick-compliment" => "Quick Compliment",
            _ => "Random Compliment",
        };
        let mut actions = Vec::new();
        let root = if self.error.is_some() || self.pending.is_some() || !self.loaded {
            let (verb, label) = match &self.pending {
                Some(p) if p.phase == Phase::Close => ("retry", "Retry Close"),
                Some(_) => ("retry", "Retry Copy"),
                None => ("load", "Retry"),
            };
            actions.push(json!({"id":self.action(verb,""),"title":label,"kind":"action"}));
            json!({"type":"Detail","props":{"markdown":self.error.clone().unwrap_or_else(||"The previous operation did not finish. Retry explicitly to continue.".into())}})
        } else {
            let mut props = json!({"isShowingDetail":true,"selectedItemId":self.effective_selected,"searchText":self.search,"__hasServerSearch":true,"onSelectionActionId":self.action("select","")});
            actions.push(json!({"id":self.action("select",""),"title":"Select","kind":"action"}));
            if self.command == "random-compliment" {
                let options: Vec<_> = domain::TONES.iter().map(|t|json!({"type":"List.Dropdown.Item","props":{"value":t,"title":match *t {"all"=>"All tones","warm"=>"Warm","playful"=>"Playful","sincere"=>"Sincere",_=>"Specific Skill"}}})).collect();
                props["searchBarAccessory"] = json!({"type":"List.Dropdown","props":{"value":self.tone,"actionId":self.action("tone",""),"tooltip":"Filter by tone"},"children":options});
                actions.push(
                    json!({"id":self.action("tone",""),"title":"Filter by tone","kind":"action"}),
                );
            }
            let children: Vec<_> = self.visible().iter().map(|r|{
                let copy = self.action("copy",&r.id); let shuffle = self.action("shuffle",&r.id);
                actions.push(json!({"id":copy,"title":if self.command == "gratitude-note" {"Copy Prompt"} else {"Copy Compliment"},"kind":"action"}));
                actions.push(json!({"id":shuffle,"title":"Shuffle","kind":"action","shortcut":{"modifiers":["cmd"],"key":"r"}}));
                json!({"type":"List.Item","props":{"id":r.id,"title":r.text,"actionIds":[copy,shuffle],"detail":{"type":"List.Item.Detail","props":{"markdown":domain::markdown(r)}}}})
            }).collect();
            json!({"type":"List","props":props,"children":children})
        };
        let mut value = tezbar_extension_sdk::view(title, root, actions);
        value["refreshMs"] = Value::Null;
        if let Some(error) = &self.error {
            value["message"] = json!(error);
        }
        value
    }
}
type Sessions = Arc<Mutex<HashMap<String, Arc<Mutex<Live>>>>>;
/// Captured *before* first polling. SDK scope drops this even for cancelled opens,
/// where SDK intentionally does not invoke extension:dispose-session.
struct Cleanup {
    sessions: Sessions,
    id: String,
    live: Arc<Mutex<Live>>,
    armed: bool,
}
impl Drop for Cleanup {
    fn drop(&mut self) {
        if self.armed {
            let mut map = self.sessions.lock().unwrap();
            if map
                .get(&self.id)
                .is_some_and(|s| Arc::ptr_eq(s, &self.live))
            {
                map.remove(&self.id);
            }
        }
    }
}
pub struct Adapter {
    sessions: Sessions,
    sample: Arc<dyn Fn() -> Result<f64, String> + Send + Sync>,
}
impl Default for Adapter {
    fn default() -> Self {
        Self::with_random(domain::os_sample)
    }
}
impl Adapter {
    /// Injectable sampling for synthetic tests only. The executable has no QA env switch.
    pub fn with_random(f: impl Fn() -> Result<f64, String> + Send + Sync + 'static) -> Self {
        Self {
            sessions: Arc::default(),
            sample: Arc::new(f),
        }
    }
    pub fn live_sessions(&self) -> usize {
        self.sessions.lock().unwrap().len()
    }
    fn load(&self, ctx: &ExtensionContext, s: &mut Live) -> Result<(), String> {
        if let Some(tone) = s.pending_tone.clone() {
            store::save(&ctx.paths.data_dir, &tone)?;
            s.tone = tone;
            s.pending_tone = None;
            s.effective(self.sample.as_ref())?;
        } else if !s.loaded {
            if s.command == "random-compliment" {
                s.tone = store::load(&ctx.paths.data_dir)?;
            }
            // Source useState samples ALL before a restored filter's effective selection.
            s.selected = domain::pick(&s.rows, None, (self.sample)()?)?;
            s.effective(self.sample.as_ref())?;
            s.loaded = true;
        }
        s.error = None;
        Ok(())
    }
    async fn effects(&self, ctx: &ExtensionContext, live: &Arc<Mutex<Live>>) -> CoreResult {
        // pending was prepared, fenced and stored BEFORE any reverse await.
        loop {
            let (phase, text, browse) = {
                let s = live.lock().unwrap();
                let p = s.pending.as_ref().ok_or("No prepared operation")?;
                (p.phase, p.text.clone(), s.command != "quick-compliment")
            };
            let request = async {
                match phase {
                    Phase::Copy => ctx.host("host.clipboard.write", json!({"text":text})).await,
                    Phase::Close => {
                        ctx.host("host.window.visibility", json!({"visible":false}))
                            .await
                    }
                    Phase::Done => unreachable!(),
                }
            };
            if phase == Phase::Done {
                return Ok(live.lock().unwrap().view());
            }
            let response =
                match tokio::time::timeout(std::time::Duration::from_secs(5), request).await {
                    Ok(result) => result,
                    Err(_) => Err("Host acknowledgement timed out".into()),
                };
            let result = match phase {
                Phase::Copy => strict_ack(response),
                Phase::Close => visibility_completion(response),
                Phase::Done => unreachable!(),
            };
            let mut s = live.lock().unwrap();
            match result {
                Ok(()) => {
                    s.pending.as_mut().unwrap().phase = if phase == Phase::Copy && browse {
                        Phase::Close
                    } else {
                        Phase::Done
                    };
                    s.error = None;
                }
                Err(_) => {
                    s.error=Some(if phase==Phase::Copy {"Copy was not acknowledged. It may have completed. Retry Copy sends the same text."} else {"Copy was acknowledged; closing was not. Retry Close does not copy again."}.into());
                    return Ok(s.view());
                }
            }
        }
    }
    async fn run(
        &self,
        ctx: &ExtensionContext,
        command: &str,
        operation: &str,
        payload: &Value,
    ) -> CoreResult {
        let id = payload["sessionId"].as_str().ok_or("Missing session ID")?;
        if id.is_empty() || id.len() > 256 {
            return Err("Invalid session ID".into());
        }
        if operation == "extension:dispose-session" {
            self.sessions.lock().unwrap().remove(id);
            return Ok(json!({"ok":true}));
        }
        let mut open_guard = None;
        let live = if operation == "extension:run-command" {
            let live = Arc::new(Mutex::new(Live {
                command: command.into(),
                rows: domain::records(command)?,
                tone: "all".into(),
                selected: None,
                effective_selected: None,
                search: String::new(),
                revision: 1,
                loaded: false,
                pending_tone: None,
                error: None,
                pending: None,
            }));
            {
                let mut map = self.sessions.lock().unwrap();
                if map.len() >= 128 || map.contains_key(id) {
                    return Err("Adapter session limit/existing ID".into());
                }
                map.insert(id.into(), live.clone());
            }
            open_guard = Some(Cleanup {
                sessions: self.sessions.clone(),
                id: id.into(),
                live: live.clone(),
                armed: true,
            });
            let owned = Cleanup {
                sessions: self.sessions.clone(),
                id: id.into(),
                live: live.clone(),
                armed: true,
            };
            ctx.spawn(async move {
                let _owned = owned;
                std::future::pending::<()>().await;
            })?;
            {
                let mut s = live.lock().unwrap();
                if let Err(e) = self.load(ctx, &mut s) {
                    s.error = Some(e);
                }
                if let Some(search) = payload.get("searchText").filter(|v| !v.is_null()) {
                    match search.as_str().filter(|s|s.len()<=4096) {Some(q)=>s.search=q.into(),None=>s.error=Some("Search exceeds 4096 UTF-8 bytes or is invalid. Retry to keep the previous search.".into())}
                }
                if command == "quick-compliment" && s.error.is_none() {
                    let text = s
                        .rows
                        .iter()
                        .find(|r| Some(&r.id) == s.selected.as_ref())
                        .ok_or("Missing random record")?
                        .text
                        .clone();
                    s.pending = Some(Pending {
                        text,
                        phase: Phase::Copy,
                    });
                }
            }
            live
        } else {
            self.sessions
                .lock()
                .unwrap()
                .get(id)
                .cloned()
                .ok_or("Session no longer active")?
        };
        let mut effect = false;
        {
            let mut s = live.lock().unwrap();
            if s.command != command {
                return Err("Session command mismatch".into());
            }
            match operation {
                "extension:run-command" => {
                    effect = s.pending.is_some();
                }
                "extension:refresh-session" | "extension:load-more" => {}
                "extension:search-text-changed" => {
                    s.bump()?;
                    match payload["searchText"].as_str().filter(|q|q.len()<=4096) {
                        Some(q)=>{s.search=q.into();if s.pending.is_none(){s.error=None;}},
                        None=>s.error=Some("Search exceeds 4096 UTF-8 bytes or is invalid. Retry to keep the previous search.".into()),
                    }
                }
                "extension:invoke-action" => {
                    let action = payload["actionId"]
                        .as_str()
                        .filter(|s| s.len() <= 512)
                        .ok_or("Invalid action ID")?;
                    let mut parts = action.splitn(3, ':');
                    let revision = parts
                        .next()
                        .and_then(|n| n.parse::<u64>().ok())
                        .ok_or("Invalid action revision")?;
                    let verb = parts.next().ok_or("Invalid action")?;
                    let row = parts.next().ok_or("Invalid action")?;
                    if revision != s.revision {
                        return Err("Stale action; use the current view".into());
                    }
                    if !s.view()["actions"].as_array().is_some_and(|actions| {
                        actions.iter().any(|a| a["id"].as_str() == Some(action))
                    }) {
                        return Err("Action is not available in the current view".into());
                    }
                    // Consume even invalid/current actions. Staged SDK rollback must
                    // never reauthorize an effect or old row/tone after A-B-A search.
                    s.bump()?;
                    if s.pending.as_ref().is_some_and(|p| p.phase == Phase::Done) {
                        return Ok(s.view());
                    }
                    if s.pending.is_some() && verb != "retry" {
                        return Err("Prepared operation requires explicit Retry".into());
                    }
                    match verb {
                        "retry" if row.is_empty() && s.pending.is_some() => effect = true,
                        "load" if row.is_empty() && s.pending.is_none() => {
                            if let Err(e) = self.load(ctx, &mut s) {
                                s.error = Some(e);
                            }
                            if command == "quick-compliment" && s.loaded && s.error.is_none() {
                                let text = s
                                    .rows
                                    .iter()
                                    .find(|r| Some(&r.id) == s.selected.as_ref())
                                    .ok_or("Missing random record")?
                                    .text
                                    .clone();
                                s.pending = Some(Pending {
                                    text,
                                    phase: Phase::Copy,
                                });
                                effect = true;
                            }
                        }
                        "tone" if command == "random-compliment" && s.loaded && row.is_empty() => {
                            let Some(tone) = payload["formValues"]["value"]
                                .as_str()
                                .filter(|v| domain::TONES.contains(v))
                            else {
                                s.error = Some(
                                    "Invalid tone input. Retry to keep the previous tone.".into(),
                                );
                                return Ok(s.view());
                            };
                            match store::save(&ctx.paths.data_dir, tone) {
                                Ok(()) => {
                                    s.tone = tone.into();
                                    if let Err(e) = s.effective(self.sample.as_ref()) {
                                        s.error = Some(e);
                                    }
                                }
                                Err(e) => {
                                    s.pending_tone = Some(tone.into());
                                    s.error = Some(e);
                                }
                            }
                        }
                        "select" if row.is_empty() && s.loaded => {
                            let selected = payload["formValues"]["value"].as_str();
                            let Some(selected) =
                                selected.filter(|v| s.visible().iter().any(|r| r.id == *v))
                            else {
                                s.error=Some("Selection is not visible. Retry to keep the current selection.".into());
                                return Ok(s.view());
                            };
                            s.selected = Some(selected.into());
                            s.effective_selected = s.selected.clone();
                        }
                        "copy" | "shuffle" if s.loaded => {
                            let record = s
                                .visible()
                                .into_iter()
                                .find(|r| r.id == row)
                                .ok_or("Row is not visible")?;
                            if verb == "copy" {
                                s.pending = Some(Pending {
                                    text: record.text,
                                    phase: Phase::Copy,
                                });
                                effect = true;
                            } else {
                                match domain::pick(
                                    &s.pool(),
                                    s.selected.as_deref(),
                                    (self.sample)()?,
                                ) {
                                    Ok(next) => {
                                        s.selected = next;
                                        s.effective_selected = s.selected.clone();
                                    }
                                    Err(e) => s.error = Some(e),
                                }
                            }
                        }
                        _ => return Err("Action is not available".into()),
                    }
                }
                _ => return Err("Unsupported operation".into()),
            }
        }
        let result = if effect {
            self.effects(ctx, &live).await
        } else {
            Ok(live.lock().unwrap().view())
        };
        if result.is_ok() {
            if let Some(guard) = &mut open_guard {
                guard.armed = false;
            }
        }
        result
    }
}
/// Clipboard write requires its closed object acknowledgement contract.
pub fn strict_ack(result: CoreResult) -> Result<(), String> {
    let value = result?;
    let obj = value.as_object().ok_or("Invalid host acknowledgement")?;
    if obj.get("ok") != Some(&Value::Bool(true))
        || obj.keys().any(|k| k != "ok" && k != "message")
        || obj.get("message").is_some_and(|m| !m.is_string())
    {
        return Err("Invalid host acknowledgement".into());
    }
    Ok(())
}
/// The pinned visibility router returns the platform's normal null completion.
pub fn visibility_completion(result: CoreResult) -> Result<(), String> {
    if result?.is_null() {
        Ok(())
    } else {
        Err("Invalid host visibility completion".into())
    }
}
impl Extension for Adapter {
    fn id(&self) -> &'static str {
        "com.tezbar.native.kind-words"
    }
    fn version(&self) -> &'static str {
        env!("CARGO_PKG_VERSION")
    }
    fn commands(&self) -> &'static [&'static str] {
        COMMANDS
    }
    fn handle<'a>(
        &'a self,
        ctx: &'a ExtensionContext,
        command: &'a str,
        operation: &'a str,
        payload: &'a Value,
        _state: &'a mut Value,
    ) -> BoxFuture<'a, CoreResult> {
        Box::pin(self.run(ctx, command, operation, payload))
    }
}
