---
title: Stockage des médias
description: Stocker les photos des recettes sur un service compatible S3.
sidebar:
  order: 4
---

Les photos ajoutées depuis l'administration sont stockées dans `MEDIA_ROOT`. Sur un hébergeur sans disque persistant, activez un stockage objet en renseignant :

```ini
AWS_STORAGE_BUCKET_NAME=comegusto-media
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_ENDPOINT_URL=https://<compte>.r2.cloudflarestorage.com   # vide pour AWS S3
AWS_S3_REGION_NAME=auto                                         # selon le fournisseur
AWS_S3_CUSTOM_DOMAIN=media.example.org                          # facultatif, bucket public
```

- Sans domaine personnalisé, les images sont servies par des URL signées ; avec un domaine public, par des URL directes mises en cache.
- Le domaine des médias est ajouté automatiquement à la Content Security Policy.
- Les fichiers existants ne sont jamais écrasés (`file_overwrite=False`) et aucune ACL n'est imposée : la visibilité se règle sur le bucket.
- **Cloudflare R2** propose 10 Go gratuits et ne facture pas la bande passante sortante. Scaleway Object Storage et Backblaze B2 sont d'autres options européennes ou peu coûteuses.

Sur un [serveur VPS](/reaco_updated/deploiement/serveur-vps/), le volume Docker `media` suffit : Caddy sert directement `/media/`.
