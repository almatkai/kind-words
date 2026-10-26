use serde::{Deserialize, Serialize};

pub const TONES: [&str; 5] = ["all", "warm", "playful", "sincere", "specific-skill"];
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct Record {
    pub id: String,
    pub text: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub tone: String,
    #[serde(default, skip_serializing_if = "String::is_empty")]
    pub context: String,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub examples: Vec<String>,
}
pub fn records(command: &str) -> Result<Vec<Record>, String> {
    let bytes = match command {
        "random-compliment" | "quick-compliment" => include_str!("../data/compliments.json"),
        "gratitude-note" => include_str!("../data/prompts.json"),
        _ => return Err("Unknown command".into()),
    };
    let rows: Vec<Record> = serde_json::from_str(bytes).map_err(|e| e.to_string())?;
    let mut ids = std::collections::HashSet::new();
    if rows.is_empty() || rows.len() > 256 {
        return Err("Invalid bundled record count".into());
    }
    for r in &rows {
        if !ids.insert(&r.id) || r.id.is_empty() || r.text.trim().is_empty() || r.text.len() > 4096
        {
            return Err("Invalid bundled record".into());
        }
        if command == "gratitude-note" {
            if r.context.trim().is_empty()
                || !(2..=3).contains(&r.examples.len())
                || r.examples
                    .iter()
                    .any(|s| s.trim().is_empty() || s.len() > 4096)
            {
                return Err("Invalid bundled prompt".into());
            }
        } else if !TONES[1..].contains(&r.tone.as_str()) {
            return Err("Invalid bundled tone".into());
        }
    }
    Ok(rows)
}
/// Math.floor(u * candidates.length), with the original exclude and ordering rules.
/// Production u comes from 53 OS-random bits, never a seeded PRNG or modulo choice.
pub fn pick(rows: &[Record], exclude: Option<&str>, u: f64) -> Result<Option<String>, String> {
    if !(0.0..1.0).contains(&u) || !u.is_finite() {
        return Err("Random sample must be finite in [0,1)".into());
    }
    let candidates: Vec<_> = rows
        .iter()
        .filter(|r| rows.len() < 2 || exclude != Some(r.id.as_str()))
        .collect();
    Ok(if candidates.is_empty() {
        None
    } else {
        Some(
            candidates[(u * candidates.len() as f64).floor() as usize]
                .id
                .clone(),
        )
    })
}
pub fn os_sample() -> Result<f64, String> {
    let mut bytes = [0; 8];
    getrandom::fill(&mut bytes).map_err(|_| "OS randomness unavailable".to_owned())?;
    Ok((u64::from_le_bytes(bytes) >> 11) as f64 / 9_007_199_254_740_992.0)
}
pub fn pool(rows: &[Record], tone: &str) -> Vec<Record> {
    rows.iter()
        .filter(|r| tone == "all" || r.tone == tone)
        .cloned()
        .collect()
}
pub fn search(rows: &[Record], text: &str) -> Vec<Record> {
    let q = text.trim().to_lowercase();
    rows.iter()
        .filter(|r| r.text.to_lowercase().contains(&q))
        .cloned()
        .collect()
}
pub fn markdown(r: &Record) -> String {
    if r.tone.is_empty() {
        let mut lines = vec![
            format!("# {}", r.text),
            String::new(),
            r.context.clone(),
            String::new(),
            "## Try opening with".into(),
            String::new(),
        ];
        lines.extend(r.examples.iter().map(|s| format!("- {s}")));
        lines.join("\n")
    } else {
        format!("# {}\n\n—\n*{}*", r.text, r.tone)
    }
}
