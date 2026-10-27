use serde_json::json;
use tezbar_kind_words::{domain::*, strict_ack, visibility_completion};
#[test]
fn original_floor_random_mapping_and_exclusion() {
    for command in ["random-compliment", "gratitude-note"] {
        let rows = records(command).unwrap();
        for tone in TONES {
            let pool = if command == "gratitude-note" {
                rows.clone()
            } else {
                pool(&rows, tone)
            };
            for exclude in [None, Some(pool[0].id.as_str()), Some("absent")] {
                let expected: Vec<_> = pool
                    .iter()
                    .filter(|r| pool.len() < 2 || exclude != Some(r.id.as_str()))
                    .collect();
                for (i, r) in expected.iter().enumerate() {
                    for offset in [0.25, 0.5, 0.99999] {
                        assert_eq!(
                            pick(&pool, exclude, (i as f64 + offset) / expected.len() as f64)
                                .unwrap()
                                .as_deref(),
                            Some(r.id.as_str())
                        );
                    }
                }
            }
        }
        assert_eq!(
            pick(&rows[..1], Some(&rows[0].id), 0.5).unwrap(),
            Some(rows[0].id.clone())
        );
    }
    assert_eq!(pick(&[], None, 0.5).unwrap(), None);
    for bad in [-1., 1., f64::NAN, f64::INFINITY] {
        assert!(pick(&[], None, bad).is_err());
    }
    for _ in 0..256 {
        assert!((0.0..1.0).contains(&os_sample().unwrap()));
    }
}
#[test]
fn strict_ack_is_closed_and_success_only() {
    for v in [
        json!(null),
        json!(true),
        json!(false),
        json!({}),
        json!({"ok":false}),
        json!({"ok":true,"error":null}),
        json!({"ok":true,"extra":1}),
        json!({"ok":true,"message":null}),
    ] {
        assert!(strict_ack(Ok(v)).is_err());
    }
    for v in [json!({"ok":true}), json!({"ok":true,"message":"synthetic"})] {
        assert!(strict_ack(Ok(v)).is_ok());
    }
    assert!(strict_ack(Err("synthetic".into())).is_err());
}
#[test]
fn full_bundled_records_order_and_unicode_are_exact() {
    for (command, source) in [
        (
            "random-compliment",
            include_str!("../fixtures/source/src/data/compliments.json"),
        ),
        (
            "gratitude-note",
            include_str!("../fixtures/source/src/data/prompts.json"),
        ),
    ] {
        assert_eq!(
            serde_json::to_value(records(command).unwrap()).unwrap(),
            serde_json::from_str::<serde_json::Value>(source).unwrap()
        );
    }
    assert_eq!(
        records("quick-compliment").unwrap(),
        records("random-compliment").unwrap()
    );
}

#[test]
fn visibility_completion_is_only_null() {
    assert!(visibility_completion(Ok(json!(null))).is_ok());
    for value in [
        json!(true),
        json!(false),
        json!({}),
        json!({"ok":true}),
        json!({"ok":true,"message":"synthetic"}),
        json!({"unknown":1}),
        json!(0),
        json!("null"),
        json!([]),
    ] {
        assert!(visibility_completion(Ok(value)).is_err());
    }
    assert!(visibility_completion(Err("synthetic host failure".into())).is_err());
}
