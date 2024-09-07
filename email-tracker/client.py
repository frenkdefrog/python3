import socket

def send_policy_request_to_service():
    host = 'localhost'  # A szerver címe, ahol a PostfixPolicyService fut
    port = 23451        # A port, ahol a PostfixPolicyService hallgatózik

    # Példa Postfix policy request adatok
    policy_data = [
        "request=smtpd_access_policy",
        "protocol_state=RCPT",
        "protocol_name=SMTP",
        "helo_name=somehelo.example.com",
        "queue_id=8045F2AB23",
        "sender=sender@example.com",
        "recipient=recipient@example.com",
        "recipient_count=1",
        "client_address=192.0.2.1",
        "client_name=another.example.com",
        "reverse_client_name=another.example.com",
        "instance=123.456.7",
        "sasl_method=plain",
        "sasl_username=sender@example.com",
        "sasl_sender=",
        "size=12345",
        "ccert_subject=",
        "ccert_issuer=",
        "ccert_fingerprint=",
        "encryption_protocol=TLSv1.2",
        "encryption_cipher=ECDHE-RSA-AES128-GCM-SHA256",
        "encryption_keysize=128",
        "etrn_domain=",
        "stress=",
        ""
    ]

    # Az üzenet elküldése a szervernek
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        for line in policy_data:
            sock.sendall(f"{line}\n".encode('utf-8'))
        sock.sendall("\n".encode('utf-8'))  # Üres sor a kommunikáció befejezéséhez
        response = sock.recv(1024)
        print('Received from server:', response.decode('utf-8'))

if __name__ == '__main__':
    send_policy_request_to_service()