# Known limitations

**English** · [Français](../fr/limitations.md)

The backup format was reverse-engineered from a few real files.
What follows is not yet covered or verified.

## On the device

- Backups produced by the tool have not yet been loaded back onto the
  device. **Always keep a copy of the original backup.**
- Samples added by the tool have not yet been listened to on the device.

## Kits

- **`KITC` kits** (the format the device writes when a kit is saved): for
  pads 1 to 8, only the values are stored, and some areas are overlaid by
  other structures of unknown purpose. The values there remain readable and
  editable; only the value byte is rewritten.
- **Slots 10 to 24**: their exact mapping to the external triggers and the
  pedals is not verified.
- Several parameters are not yet identified (see
  [Parameters](parameters.md#unidentified-parameters)), nor are the kit settings
  other than name, volume and tempo (time signature, logo, effects).

## Samples

- Adding verified up to id 8099 (folder `080`). Beyond that, the tool refuses.
- Deleting or replacing a sample is not supported.
- Factory samples are not included in backups: they can be neither
  listened to nor exported.
- `.had` headers truncate names to 16 characters; `samples.json` gives
  the full names.

## `.fac` backups

They contain only kits: samples cannot be added to them.
