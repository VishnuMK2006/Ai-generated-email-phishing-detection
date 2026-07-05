import fs from "fs";
import readline from "readline";
import { romanize } from "tamil-romanizer";

const inputFile = "chatgpt_translated_tamil.jsonl";
const outputFile = "chatgpt_tamil_tanglish.jsonl";

const rl = readline.createInterface({
    input: fs.createReadStream(inputFile, { encoding: "utf8" }),
    crlfDelay: Infinity
});

const writer = fs.createWriteStream(outputFile, {
    encoding: "utf8"
});

let count = 0;

try {
    for await (const line of rl) {
        if (!line.trim()) continue;

        // Fix invalid JSON values produced by pandas
        const fixedLine = line.replace(/\bNaN\b/g, "null");

        let record;

        try {
            record = JSON.parse(fixedLine);
        } catch (err) {
            console.error(`Error parsing line ${count + 1}:`, err.message);
            continue;
        }

        record.tanglish_subject =
            typeof record.tamil_subject === "string"
                ? romanize(record.tamil_subject)
                : "";

        record.tanglish_body =
            typeof record.tamil_body === "string"
                ? romanize(record.tamil_body)
                : "";

        writer.write(
            JSON.stringify(record, null, 0) + "\n",
            "utf8"
        );

        count++;

        // if (count >= 10) {
        //     break;
        // }
    }

    console.log(`Processed ${count} records.`);
    console.log(`Saved to ${outputFile}`);
} catch (err) {
    console.error("Unexpected error:", err);
} finally {
    writer.end();
}