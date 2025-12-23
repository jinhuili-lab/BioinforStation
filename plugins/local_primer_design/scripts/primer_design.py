def run(dna_seq: str, tm: float = 60.0, primer_length: int = 20):
    seq = ''.join(dna_seq.split()).upper()
    primers = []
    if len(seq) < primer_length * 2:
        return {'primers': primers}
    left = seq[:primer_length]
    right = seq[-primer_length:]
    primers.append({'name': 'F1', 'sequence': left, 'length': len(left)})
    primers.append({'name': 'R1', 'sequence': right, 'length': len(right)})
    return {'primers': primers}
