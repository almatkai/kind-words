#!/usr/bin/env python3
"""Compile exact pinned visibility match arms; replace only desktop producer boundaries."""
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parents[1]
base = root / 'fixtures/host/src-tauri/src/native_core'
router = (base / 'extensions/process_host.rs').read_text()
platform = (base / 'platform.rs').read_text()
# Retain both selected arms verbatim, including their result/argument/error flow.
# These explicit next-arm delimiters fail closed if the frozen layout changes.
route = router[router.index('            "host.window.visibility"=>'):router.index('            "host.dialog.confirm"=>')]
operation = platform[platform.index('            "core:platform:visibility" =>'):platform.index('            "core:platform:suppress-blur"')]
header = '''// Generated from pinned Tezbar ea100cee3f69711de12485ba061950c5fc65258f.
// Apache-2.0: fixtures/host/LICENSE. Match arms unchanged; surrounding harness synthetic.
use serde_json::{json, Value};
type CoreResult = Result<Value, String>;
#[derive(Default)]
pub struct Backend { calls: std::sync::Mutex<Vec<bool>> }
// Desktop producer boundary: record only, never access the app/window/OS.
pub fn set_backend_app_visibility(app: &Backend, visible: bool) {
    app.calls.lock().unwrap().push(visible);
}
struct Platform { backend: Backend, available: bool }
impl Platform {
    fn app(&self) -> Result<&Backend, String> {
        if self.available { Ok(&self.backend) } else { Err("synthetic desktop unavailable".into()) }
    }
    async fn request(&self, channel: &str, args: Vec<Value>) -> CoreResult {
        let value = args.first().cloned().unwrap_or(Value::Null);
        match channel {
'''
middle = '''            _ => Err("unexpected platform operation".into()),
        }
    }
}
struct Host { ctx: Platform }
impl Host {
    async fn call(&self, method: &str, params: Value) -> CoreResult {
        match method {
'''
tail = '''            _ => Err("unexpected reverse method".into()),
        }
    }
}
fn host(available: bool) -> Host {
    Host {ctx: Platform {backend: Backend::default(), available}}
}
pub async fn contract() -> Value {
    let host = host(true);
    let result = host.call("host.window.visibility", json!({"visible":false})).await.unwrap();
    assert_eq!(*host.ctx.backend.calls.lock().unwrap(), vec![false]);
    json!({"visibility":result,
        "platformSource":include_str!("../host/src-tauri/src/native_core/platform.rs"),
        "routerSource":include_str!("../host/src-tauri/src/native_core/extensions/process_host.rs")})
}
#[tokio::test]
async fn pinned_visibility_router_and_platform_completion() {
    assert!(contract().await["visibility"].is_null());
    let host = host(true);
    for visible in [false, true] {
        assert_eq!(host.call("host.window.visibility", json!({"visible":visible})).await.unwrap(), Value::Null);
    }
    assert_eq!(*host.ctx.backend.calls.lock().unwrap(), vec![false,true]);
    for bad in [json!({}),json!({"visible":null}),json!({"visible":0})] {
        assert!(host.call("host.window.visibility", bad).await.is_err());
    }
    assert_eq!(*host.ctx.backend.calls.lock().unwrap(), vec![false,true]);
    let unavailable = self::host(false);
    assert!(unavailable.call("host.window.visibility", json!({"visible":false})).await.is_err());
    assert!(unavailable.ctx.backend.calls.lock().unwrap().is_empty());
}
'''
out = root / 'fixtures/host-extracted/visibility.rs'
out.write_text(header + operation + middle + route + tail)
subprocess.run(['rustfmt', '--edition', '2021', str(out)], check=True)
print('Prepared executable pinned visibility router/platform arms; desktop producer mocked only.')
