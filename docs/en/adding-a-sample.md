# Adding a sample

**English** · [Français](../fr/adding-a-sample.md)

Samples can only be added to a `.bkf` backup
(*Save All User Kits*), the only one that contains user samples.

## Required format

PCM WAV, **16-bit, 44.1 kHz**, mono or stereo, as for an import on the device.
The file is copied as is, without conversion. A WAV in another format is
refused with a message stating the format received.

## With the web editor

In the sample selection window (the sample button of a wave), drag and drop
the file onto the *Ajouter un WAV* (Add a WAV) area or click it. The sample is
added, then selected for the current wave. See [Web editor](web-editor.md).

## From the command line

1. Export the backup (see [Editing a kit](editing-a-kit.md)).
2. Put the file in the export's `wav/` folder, for example
   `my_kits/wav/My Snare.wav`.
3. Refer to it by its name, without `.wav`, in a kit:

   ```json
   "wave_a": { "sample": "My Snare" }
   ```

4. Run the import: the sample is added, then the kits are applied.

```bash
python3 -m strike_kits import Backup001.bkf my_kits -o Backup002.bkf
# sample 'My Snare' ajouté (id 8073)
```

## Rules

- The sample name is the file name. It must be unique: the device
  appends `_id` to duplicate names, the tool refuses them.
- A WAV in the `wav/` folder is **ignored** if its name already exists among the
  samples, or if its content is identical to that of a user sample. The `wav/`
  folder produced by the export can therefore stay in place, even if a file is
  renamed: the import can be rerun as many times as needed without creating
  duplicates.
- The sample gets the next free id (8073, 8074…) and joins the
  *User > New Sample* category, like an import done on the device.
- The rules applied (`.had` files, five index lists, counters) were
  recorded on a backup made by the device before and after an import:
  the tool reproduces that result byte for byte. Details:
  [adding a sample](bkf-format.md#adding-a-sample-observed-on-the-device).

## Limitations

- Adding verified up to id 8099 (folder `080`). Beyond that, the tool refuses
  out of caution: how the device names the following folders has not been
  observed.
- Deleting or replacing a sample is not supported.
- Factory samples are not in the backup: they can be neither listened to nor
  exported, only referenced by their id or name.
