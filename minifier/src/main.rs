extern crate minifier;

use std::env;
use std::fs::{File, read_dir};
use std::io::{Read, Write};
use std::path::Path;

use minifier::css;
use minifier::js::{self, Keyword, ReservedChar, Token};

fn read_file(file_path: &Path) -> String {
    let mut f = match File::open(file_path) {
        Ok(f) => f,
        Err(e) => panic!("failed to open \"{}\": {}", file_path.display(), e),
    };
    let mut data = Vec::new();
    match f.read_to_end(&mut data) {
        Err(e) => panic!("failed to read \"{}\": {}", file_path.display(), e),
        _ => {}
    }
    match String::from_utf8(data) {
        Ok(s) => s,
        Err(e) => panic!("failed to convert to UTF8 while reading \"{}\": {}",
                         file_path.display(), e),
    }
}

fn write_to_file(file_path: &Path, content: &str) {
    let mut f = match File::create(file_path) {
        Ok(f) => f,
        Err(e) => panic!("failed to open/create \"{}\": {}", file_path.display(), e),
    };
    match writeln!(f, "{}", content) {
        Err(e) => panic!("failed to write into \"{}\": {}", file_path.display(), e),
        _ => {}
    }
}

fn minify_search_index(file_path: &Path) {
    print!("\"{}\" => ", file_path.display());
    let content = read_file(file_path);
    print!("FROM {} bytes ", content.len());

    let f: js::Tokens<'_> = js::simple_minify(&content)
                               .into_iter()
                               .filter(|f| {
                                   // We keep backlines.
                                   minifier::js::clean_token_except(f, &|c: &Token<'_>| {
                                       c.get_char() != Some(ReservedChar::Backline)
                                   })
                               })
                               .map(|f| {
                                   minifier::js::replace_token_with(f, &|t: &Token<'_>| {
                                       match *t {
                                           Token::Keyword(Keyword::Null) => Some(Token::Other("N")),
                                           Token::String(s) => {
                                               let s = &s[1..s.len() -1]; // The quotes are included
                                               if s.is_empty() {
                                                   Some(Token::Other("E"))
                                               } else if s == "t" {
                                                   Some(Token::Other("T"))
                                               } else if s == "u" {
                                                   Some(Token::Other("U"))
                                               } else {
                                                   None
                                               }
                                           }
                                           _ => None,
                                       }
                                   })
                               })
                               .collect::<Vec<_>>()
                               .into();
    let f = f.apply(|f| {
        // We add a backline after the newly created variables.
        minifier::js::aggregate_strings_into_array_with_separation(
            f,
            "R",
            Token::Char(ReservedChar::Backline),
        )
    })
    .to_string();
    println!("TO {}", f.len());
    write_to_file(file_path, &f.replace("var searchIndex={}",
                                        "var N=null,E=\"\",T=\"t\",U=\"u\",searchIndex={}"));
}

fn minify_js_file(file_path: &Path) {
    print!("\"{}\" => ", file_path.display());
    let content = read_file(file_path);
    print!("FROM {} bytes ", content.len());
    let f = js::minify(&content).to_string();
    println!("TO {}", f.len());
    write_to_file(file_path, &f);
}

fn minify_css_file(file_path: &Path) {
    print!("\"{}\" => ", file_path.display());
    let content = read_file(file_path);
    print!("FROM {} bytes ", content.len());
    let f = css::minify(&content).expect("css minification failed");
    println!("TO {}", f.len());
    write_to_file(file_path, &f);
}

fn main() {
    let args = env::args().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        panic!("Expected the doc folder as first argument");
    }

    let doc_folder = Path::new(&args[0]);
    if !doc_folder.is_dir() {
        panic!("\"{}\" isn't a folder...");
    }

    println!("Starting...");
    let mut done = 0;
    let entries = read_dir(doc_folder).expect("failed to read dir");
    for entry in entries {
        let entry = entry.expect("failed to get entry");
        if !entry.path().is_file() {
            continue;
        }
        match entry.file_name().into_string().expect("failed to get file name").as_str() {
            "search-index.js" => minify_search_index(&entry.path()),
            s if s.ends_with(".js") => minify_js_file(&entry.path()),
            s if s.ends_with(".css") => minify_css_file(&entry.path()),
            _ => continue,
        }
        done += 1;
    }
    println!("Done! (minified {} files)", done);
}
