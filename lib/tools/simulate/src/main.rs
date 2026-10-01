fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        println!("utrp-sim --events 24 --seed 42 [--config PATH] [--key C] [--mode ionian]\nUses the same library and event order as the TUI. --measures is an alias for --events.\n--key / --mode restrict scope; --threshold is minimum phrases before modulation.");
        return Ok(());
    }
    utrp::simulator::run(&utrp::simulator::Options::parse(&args)?)
}
